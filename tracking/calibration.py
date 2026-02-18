"""Calibration system for finger press detection using angle-based thresholds."""

import json
import os
import time
from typing import Dict, Optional, List
from game.constants import (
    CALIBRATION_FILE, FINGER_NAMES, FINGER_DISPLAY_NAMES,
    FINGER_PRESS_THRESHOLD, FINGER_PRESS_ANGLE_THRESHOLD
)

# Finger groups by hand
LEFT_FINGERS = ['left_pinky', 'left_ring', 'left_middle', 'left_index', 'left_thumb']
RIGHT_FINGERS = ['right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_pinky']


class CalibrationManager:
    """Manages calibration data for finger press detection using angle-based thresholds."""

    def __init__(self, calibration_file: str = CALIBRATION_FILE):
        """Initialize the calibration manager."""
        self.calibration_file = calibration_file
        self.calibration_data = {}
        self.is_calibrated = False

        # Default thresholds (Y-position based, for backward compatibility)
        self.thresholds = {name: FINGER_PRESS_THRESHOLD for name in FINGER_NAMES}

        # Angle-based thresholds
        self.angle_thresholds = {name: FINGER_PRESS_ANGLE_THRESHOLD for name in FINGER_NAMES}
        self.baseline_angles = {name: None for name in FINGER_NAMES}
        self.angle_calculation_mode: Optional[str] = None

        # Calibration process state
        self.calibrating = False
        self.current_finger_index = 0
        self.calibration_phase = 'idle'
        # Phases: 'countdown', 'baseline_left', 'baseline_right', 'calibrating_finger', 'complete'

        # Countdown state (time to place hands after pressing SPACE)
        self.countdown_start = 0
        self.countdown_duration = 5.0  # 5 seconds to place hands

        # Baseline capture state
        self.baseline_samples = {name: [] for name in FINGER_NAMES}
        self.baseline_sample_count = 60  # More samples over time
        self.baseline_duration = 5.0  # 5 seconds for baseline capture
        self.baseline_start_time = 0
        self.left_baseline_captured = False
        self.right_baseline_captured = False

        # Palm position tracking (for hand position overlay)
        self.palm_position_samples = {'left': [], 'right': []}
        self.calibrated_palm_positions = {'left': None, 'right': None}

        # Current finger angle tracking
        self.current_finger_angle = 0.0
        self.current_finger_angle_from_baseline = 0.0

        # Timing
        self.last_sample_time = 0
        self.sample_delay = 0.05  # 50ms between samples
        self.phase_start_time = 0

        # Auto-advance hold time (must hold at threshold for this long)
        self.hold_time_required = 0.5  # 500ms
        self.threshold_reached_time = None

        # Load existing calibration if available
        self._load_calibration()

    def _load_calibration(self) -> bool:
        """Load calibration data from file."""
        if not os.path.exists(self.calibration_file):
            return False

        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)

            self.calibration_data = data.get('calibration_data', {})
            self.thresholds = data.get('thresholds', self.thresholds)
            self.angle_thresholds = data.get('angle_thresholds', self.angle_thresholds)
            self.baseline_angles = data.get('baseline_angles', self.baseline_angles)
            self.angle_calculation_mode = data.get('angle_calculation_mode', self.angle_calculation_mode)
            self.calibrated_palm_positions = data.get('palm_positions', {'left': None, 'right': None})
            self.is_calibrated = True
            print("Loaded existing calibration data.")
            return True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to load calibration: {e}")
            return False

    def _save_calibration(self):
        """Save calibration data to file."""
        data = {
            'thresholds': self.thresholds,
            'angle_thresholds': self.angle_thresholds,
            'baseline_angles': self.baseline_angles,
            'angle_calculation_mode': self.angle_calculation_mode,
            'calibration_data': self.calibration_data,
            'palm_positions': self.calibrated_palm_positions,
            'timestamp': time.time(),
        }

        try:
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=2)
            print("Calibration data saved.")
        except IOError as e:
            print(f"Failed to save calibration: {e}")

    def has_calibration(self) -> bool:
        """Check if calibration data exists."""
        return self.is_calibrated

    def get_threshold(self, finger_name: str) -> float:
        """Get the press threshold for a specific finger (Y-position based)."""
        return self.thresholds.get(finger_name, FINGER_PRESS_THRESHOLD)

    def get_angle_threshold(self, finger_name: str) -> float:
        """Get the angle threshold for a specific finger."""
        return self.angle_thresholds.get(finger_name, FINGER_PRESS_ANGLE_THRESHOLD)

    def get_baseline_angle(self, finger_name: str) -> Optional[float]:
        """Get the baseline angle for a specific finger."""
        return self.baseline_angles.get(finger_name)

    def set_angle_calculation_mode(self, mode: Optional[str]):
        """Store the angle calculation mode used during calibration."""
        self.angle_calculation_mode = mode

    def get_angle_calculation_mode(self) -> Optional[str]:
        """Get the angle calculation mode stored with calibration."""
        return self.angle_calculation_mode

    def get_calibrated_palm_positions(self) -> Dict:
        """Get the calibrated palm positions for both hands."""
        return self.calibrated_palm_positions

    def check_hand_positions(self, current_hand_data: Dict, tolerance: float = 50.0) -> Dict:
        """
        Check if current hand positions match calibration positions.

        Args:
            current_hand_data: Current hand tracking data
            tolerance: Distance tolerance in mm (default 50mm)

        Returns:
            Dictionary with 'left_in_position', 'right_in_position', 'both_in_position',
            and distance info for each hand
        """
        result = {
            'left_in_position': False,
            'right_in_position': False,
            'both_in_position': False,
            'left_distance': None,
            'right_distance': None,
        }

        for hand_type in ['left', 'right']:
            calibrated_pos = self.calibrated_palm_positions.get(hand_type)
            current_hand = current_hand_data.get(hand_type)

            if calibrated_pos is None:
                continue

            if current_hand is None:
                continue

            current_pos = current_hand.get('palm_position')
            if current_pos is None:
                continue

            # Calculate distance between current and calibrated position
            distance = (
                (current_pos[0] - calibrated_pos[0]) ** 2 +
                (current_pos[1] - calibrated_pos[1]) ** 2 +
                (current_pos[2] - calibrated_pos[2]) ** 2
            ) ** 0.5

            result[f'{hand_type}_distance'] = distance
            result[f'{hand_type}_in_position'] = distance <= tolerance

        # Check if both hands are in position (or if only one hand has calibration data)
        left_ok = result['left_in_position'] or self.calibrated_palm_positions.get('left') is None
        right_ok = result['right_in_position'] or self.calibrated_palm_positions.get('right') is None
        result['both_in_position'] = left_ok and right_ok

        return result

    def start_calibration(self):
        """Start the calibration process with countdown."""
        self.calibrating = True
        self.current_finger_index = 0
        self.calibration_phase = 'countdown'
        self.countdown_start = time.time()
        self.baseline_samples = {name: [] for name in FINGER_NAMES}
        self.palm_position_samples = {'left': [], 'right': []}
        self.left_baseline_captured = False
        self.right_baseline_captured = False
        self.calibration_data = {}
        self.phase_start_time = time.time()
        self.threshold_reached_time = None
        self.current_finger_angle = 0.0
        self.current_finger_angle_from_baseline = 0.0
        print("Starting calibration... Place your LEFT hand above the sensor.")

    def get_current_finger(self) -> Optional[str]:
        """Get the finger currently being calibrated."""
        # Only return a finger when we're actually calibrating individual fingers
        if self.calibration_phase != 'calibrating_finger':
            return None
        if self.current_finger_index < len(FINGER_NAMES):
            return FINGER_NAMES[self.current_finger_index]
        return None

    def get_current_finger_display(self) -> str:
        """Get display name of current finger."""
        if self.current_finger_index < len(FINGER_DISPLAY_NAMES):
            return FINGER_DISPLAY_NAMES[self.current_finger_index]
        return ""

    def get_countdown_remaining(self) -> float:
        """Get remaining countdown time in seconds."""
        if self.calibration_phase != 'countdown':
            return 0
        elapsed = time.time() - self.countdown_start
        return max(0, self.countdown_duration - elapsed)

    def get_baseline_time_remaining(self) -> float:
        """Get remaining baseline capture time in seconds."""
        if self.calibration_phase not in ['baseline_left', 'baseline_right']:
            return 0
        elapsed = time.time() - self.baseline_start_time
        return max(0, self.baseline_duration - elapsed)

    def get_calibration_status(self) -> Dict:
        """Get current calibration status."""
        return {
            'calibrating': self.calibrating,
            'current_finger': self.get_current_finger(),
            'current_finger_display': self.get_current_finger_display(),
            'finger_index': self.current_finger_index,
            'total_fingers': len(FINGER_NAMES),
            'phase': self.calibration_phase,
            'countdown_remaining': self.get_countdown_remaining(),
            'baseline_time_remaining': self.get_baseline_time_remaining(),
            'left_baseline_captured': self.left_baseline_captured,
            'right_baseline_captured': self.right_baseline_captured,
            'current_angle': self.current_finger_angle,
            'angle_from_baseline': self.current_finger_angle_from_baseline,
            'threshold_angle': FINGER_PRESS_ANGLE_THRESHOLD,
            'progress': self.current_finger_index / len(FINGER_NAMES),
            'threshold_reached': self.threshold_reached_time is not None,
            'hold_progress': self._get_hold_progress(),
        }

    def _get_hold_progress(self) -> float:
        """Get progress of holding at threshold (0.0 to 1.0)."""
        if self.threshold_reached_time is None:
            return 0.0
        elapsed = time.time() - self.threshold_reached_time
        return min(1.0, elapsed / self.hold_time_required)

    def update_calibration(self, hand_data: Dict, finger_angles: Dict) -> bool:
        """
        Update calibration with current hand data and finger angles.

        Args:
            hand_data: Current hand tracking data
            finger_angles: Dictionary of finger angles from hand tracker

        Returns:
            True if calibration is still in progress
        """
        if not self.calibrating:
            return False

        current_time = time.time()

        # Phase: Countdown before starting
        if self.calibration_phase == 'countdown':
            if current_time - self.countdown_start >= self.countdown_duration:
                # Countdown complete, start baseline capture for left hand
                self.calibration_phase = 'baseline_left'
                self.baseline_start_time = current_time
                print("Countdown complete. Capturing LEFT hand baseline - keep fingers RELAXED...")
            return True

        # Phase: Capturing baseline for LEFT hand
        if self.calibration_phase == 'baseline_left':
            return self._update_baseline_capture(hand_data, finger_angles, current_time, 'left')

        # Phase: Capturing baseline for RIGHT hand
        if self.calibration_phase == 'baseline_right':
            return self._update_baseline_capture(hand_data, finger_angles, current_time, 'right')

        # Phase: Calibrating individual fingers
        if self.calibration_phase == 'calibrating_finger':
            return self._update_finger_calibration(hand_data, finger_angles, current_time)

        return True

    def _update_baseline_capture(self, hand_data: Dict, finger_angles: Dict,
                                  current_time: float, hand_type: str) -> bool:
        """Capture baseline angles for one hand."""
        fingers = LEFT_FINGERS if hand_type == 'left' else RIGHT_FINGERS
        hand = hand_data.get(hand_type)

        # Check if time is up
        time_elapsed = current_time - self.baseline_start_time
        if time_elapsed >= self.baseline_duration:
            # Calculate baseline averages for this hand
            for finger_name in fingers:
                samples = self.baseline_samples.get(finger_name, [])
                if samples:
                    avg = sum(samples) / len(samples)
                    self.baseline_angles[finger_name] = avg
                    print(f"Baseline for {finger_name}: {avg:.1f} degrees ({len(samples)} samples)")
                else:
                    # No samples - use 0 as default
                    self.baseline_angles[finger_name] = 0.0
                    print(f"Warning: No samples for {finger_name}, using 0 as baseline")

            # Calculate average palm position for this hand
            palm_samples = self.palm_position_samples.get(hand_type, [])
            if palm_samples:
                avg_x = sum(p[0] for p in palm_samples) / len(palm_samples)
                avg_y = sum(p[1] for p in palm_samples) / len(palm_samples)
                avg_z = sum(p[2] for p in palm_samples) / len(palm_samples)
                self.calibrated_palm_positions[hand_type] = (avg_x, avg_y, avg_z)
                print(f"Palm position for {hand_type} hand: ({avg_x:.1f}, {avg_y:.1f}, {avg_z:.1f})")

            # Move to next phase
            if hand_type == 'left':
                self.left_baseline_captured = True
                self.calibration_phase = 'countdown_right'
                self.countdown_start = current_time
                print("LEFT hand baseline captured. Press fingers when ready for RIGHT hand baseline.")
                # Actually, let's just transition with a short pause
                self.calibration_phase = 'baseline_right'
                self.baseline_start_time = current_time
                print("Now capturing RIGHT hand baseline - keep fingers RELAXED...")
            else:
                self.right_baseline_captured = True
                self.calibration_phase = 'calibrating_finger'
                self.current_finger_index = 0  # Start with first finger (left_pinky)
                self.phase_start_time = current_time
                print("Baselines captured. Now calibrating individual fingers...")
                print(f"Press {self.get_current_finger()} down past {FINGER_PRESS_ANGLE_THRESHOLD} degrees")

            return True

        # Collect samples if hand is visible
        if hand is not None and current_time - self.last_sample_time >= self.sample_delay:
            self.last_sample_time = current_time
            for finger_name in fingers:
                angle = finger_angles.get(finger_name, 0.0)
                self.baseline_samples[finger_name].append(angle)

            # Also collect palm position samples
            palm_pos = hand.get('palm_position')
            if palm_pos:
                self.palm_position_samples[hand_type].append(palm_pos)

        return True

    def _update_finger_calibration(self, hand_data: Dict, finger_angles: Dict, current_time: float) -> bool:
        """Calibrate individual fingers by detecting when they reach the threshold angle."""
        current_finger = self.get_current_finger()
        if not current_finger:
            self._complete_calibration()
            return False

        # Check if the correct hand is visible
        hand_type = 'left' if 'left' in current_finger else 'right'
        if hand_data.get(hand_type) is None:
            self.threshold_reached_time = None
            return True

        # Get current angle and angle from baseline
        current_angle = finger_angles.get(current_finger, 0.0)
        baseline = self.baseline_angles.get(current_finger, 0.0)
        angle_from_baseline = current_angle - baseline

        self.current_finger_angle = current_angle
        self.current_finger_angle_from_baseline = angle_from_baseline

        # Check if finger has reached threshold
        if angle_from_baseline >= FINGER_PRESS_ANGLE_THRESHOLD:
            if self.threshold_reached_time is None:
                self.threshold_reached_time = current_time
                print(f"{current_finger} reached threshold ({angle_from_baseline:.1f} degrees)")

            # Check if held long enough
            if current_time - self.threshold_reached_time >= self.hold_time_required:
                self._calibrate_current_finger(current_angle, baseline, angle_from_baseline)
                self._advance_to_next_finger()
        else:
            # Reset hold timer if finger moved back
            if self.threshold_reached_time is not None:
                self.threshold_reached_time = None

        return True

    def _calibrate_current_finger(self, current_angle: float, baseline: float, angle_from_baseline: float):
        """Record calibration for the current finger."""
        finger_name = self.get_current_finger()

        # Store calibration data
        self.angle_thresholds[finger_name] = FINGER_PRESS_ANGLE_THRESHOLD
        self.calibration_data[finger_name] = {
            'baseline_angle': baseline,
            'calibrated_angle': current_angle,
            'angle_threshold': FINGER_PRESS_ANGLE_THRESHOLD,
            'recorded_press_angle': angle_from_baseline,
        }

        print(f"Calibrated {finger_name}: baseline={baseline:.1f}, press_angle={angle_from_baseline:.1f}")

    def _advance_to_next_finger(self):
        """Advance to next finger in calibration sequence."""
        self.current_finger_index += 1
        self.threshold_reached_time = None
        self.current_finger_angle = 0.0
        self.current_finger_angle_from_baseline = 0.0

        if self.current_finger_index >= len(FINGER_NAMES):
            self._complete_calibration()
        else:
            self.phase_start_time = time.time()
            next_finger = self.get_current_finger()
            print(f"Moving to next finger: {next_finger}")

    def _complete_calibration(self):
        """Complete the calibration process."""
        self.calibrating = False
        self.calibration_phase = 'complete'
        self.is_calibrated = True
        self._save_calibration()
        print("Calibration complete!")

    def cancel_calibration(self):
        """Cancel the calibration process."""
        self.calibrating = False
        self.calibration_phase = 'idle'
        self.current_finger_index = 0
        self.baseline_samples = {name: [] for name in FINGER_NAMES}
        self.threshold_reached_time = None
        print("Calibration cancelled.")

    def reset_calibration(self):
        """Reset all calibration data."""
        self.calibration_data = {}
        self.thresholds = {name: FINGER_PRESS_THRESHOLD for name in FINGER_NAMES}
        self.angle_thresholds = {name: FINGER_PRESS_ANGLE_THRESHOLD for name in FINGER_NAMES}
        self.baseline_angles = {name: None for name in FINGER_NAMES}
        self.is_calibrated = False

        if os.path.exists(self.calibration_file):
            try:
                os.remove(self.calibration_file)
                print("Calibration file deleted.")
            except IOError:
                pass

    def get_instructions(self) -> str:
        """Get instruction text for current calibration phase."""
        if not self.calibrating:
            return ""

        if self.calibration_phase == 'countdown':
            remaining = int(self.get_countdown_remaining()) + 1
            return f"Place your LEFT hand above the sensor... {remaining}"

        if self.calibration_phase == 'baseline_left':
            remaining = int(self.get_baseline_time_remaining()) + 1
            return f"LEFT hand: Keep ALL fingers RELAXED ({remaining}s)"

        if self.calibration_phase == 'baseline_right':
            remaining = int(self.get_baseline_time_remaining()) + 1
            return f"RIGHT hand: Keep ALL fingers RELAXED ({remaining}s)"

        if self.calibration_phase == 'calibrating_finger':
            finger = self.get_current_finger_display()
            finger_full = self.get_current_finger()

            if not finger_full:
                return ""

            hand = "LEFT" if "left" in finger_full else "RIGHT"
            finger_name = finger_full.split('_')[1].upper()

            if self.threshold_reached_time is not None:
                hold_progress = self._get_hold_progress()
                return f"HOLD {hand} {finger_name} - {int(hold_progress * 100)}%"
            else:
                return f"Press {hand} {finger_name} down past {FINGER_PRESS_ANGLE_THRESHOLD} degrees"

        return ""

    # Legacy method for compatibility
    def confirm_phase_transition(self):
        """Legacy method - no longer needed with auto-advance."""
        pass
