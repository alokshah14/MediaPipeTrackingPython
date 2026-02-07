"""Session data logger for tracking finger presses and hand positions."""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .kinematics import TrialMetrics


class SessionLogger:
    """Logs all finger presses and hand tracking data during a game session."""

    def __init__(self, log_directory: str = "data/session_logs"):
        """
        Initialize the session logger.

        Args:
            log_directory: Directory to store session log files
        """
        self.log_directory = log_directory
        self.session_id = None
        self.session_file = None
        self.session_data = None
        self.session_start_time = None

        # Ensure log directory exists
        os.makedirs(log_directory, exist_ok=True)

    def start_session(self, calibration_data: Dict = None, game_mode: str = "Unknown", is_test_mode: bool = False):
        """
        Start a new logging session.

        Args:
            calibration_data: Optional calibration data to include in session
            game_mode: The name of the game being played
            is_test_mode: Whether the session is running in test mode
        """
        self.session_start_time = time.time()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(
            self.log_directory,
            f"session_{self.session_id}.json"
        )

        self.session_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "start_timestamp": self.session_start_time,
            "game_mode": game_mode,
            "is_test_mode": is_test_mode,
            "calibration_used": calibration_data,
            "events": [],
            "summary": {
                "total_presses": 0,
                "correct_presses": 0,
                "wrong_presses": 0,
                "missiles_missed": 0,
                "accuracy": 0.0,
                "clean_trials": 0,
                "coupled_keypresses": 0,
                "average_mlr": 0.0,
                "average_reaction_time_ms": 0.0,
            },
            "mlr_values": [],  # For calculating running average
            "reaction_times": [],  # For calculating running average
        }

        self._save_session()
        print(f"Session logging started: {self.session_file}")

    def log_finger_press(
        self,
        finger_pressed: str,
        target_finger: Optional[str],
        is_correct: bool,
        left_hand_data: Optional[Dict],
        right_hand_data: Optional[Dict],
        score: int,
        lives: int,
        difficulty: str,
        trial_metrics: Optional['TrialMetrics'] = None
    ):
        """
        Log a finger press event with full hand tracking data and biomechanical metrics.

        Args:
            finger_pressed: Name of the finger that was pressed
            target_finger: Name of the target finger (None if no target)
            is_correct: Whether the press was correct
            left_hand_data: Full tracking data for left hand
            right_hand_data: Full tracking data for right hand
            score: Current score
            lives: Current lives
            difficulty: Current difficulty level
            trial_metrics: Optional biomechanical metrics from kinematics processor
        """
        if not self.session_data:
            return

        current_time = time.time()
        elapsed = current_time - self.session_start_time

        event = {
            "type": "finger_press",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "finger_pressed": finger_pressed,
            "target_finger": target_finger,
            "is_correct": is_correct,
            "game_state": {
                "score": score,
                "lives": lives,
                "difficulty": difficulty or "N/A",
            },
            "hand_tracking": {
                "left_hand": self._extract_hand_data(left_hand_data),
                "right_hand": self._extract_hand_data(right_hand_data),
            }
        }

        # Add biomechanical metrics if available
        if trial_metrics:
            event["biomechanics"] = {
                "reaction_time_ms": round(trial_metrics.reaction_time_ms, 2),
                "is_wrong_finger": trial_metrics.is_wrong_finger,
                "motion_leakage_ratio": round(trial_metrics.motion_leakage_ratio, 4),
                "target_path_length_mm": round(trial_metrics.target_path_length, 2),
                "coupled_keypress": trial_metrics.coupled_keypress,
                "is_clean_trial": trial_metrics.is_clean_trial,
                "non_target_path_lengths": {
                    k: round(v, 2) for k, v in trial_metrics.non_target_path_lengths.items()
                }
            }

        self.session_data["events"].append(event)

        # Update summary
        self.session_data["summary"]["total_presses"] += 1
        if is_correct:
            self.session_data["summary"]["correct_presses"] += 1
        else:
            self.session_data["summary"]["wrong_presses"] += 1

        total = self.session_data["summary"]["total_presses"]
        correct = self.session_data["summary"]["correct_presses"]
        self.session_data["summary"]["accuracy"] = round(correct / total * 100, 2)

        # Update biomechanical summary if metrics available
        if trial_metrics:
            if trial_metrics.is_clean_trial:
                self.session_data["summary"]["clean_trials"] += 1
            if trial_metrics.coupled_keypress:
                self.session_data["summary"]["coupled_keypresses"] += 1

            # Track MLR and reaction time for averages
            if trial_metrics.motion_leakage_ratio != float('inf'):
                self.session_data["mlr_values"].append(trial_metrics.motion_leakage_ratio)
                avg_mlr = sum(self.session_data["mlr_values"]) / len(self.session_data["mlr_values"])
                self.session_data["summary"]["average_mlr"] = round(avg_mlr, 4)

            if trial_metrics.reaction_time_ms > 0:
                self.session_data["reaction_times"].append(trial_metrics.reaction_time_ms)
                avg_rt = sum(self.session_data["reaction_times"]) / len(self.session_data["reaction_times"])
                self.session_data["summary"]["average_reaction_time_ms"] = round(avg_rt, 2)

        self._save_session()

    def log_missile_missed(
        self,
        target_finger: str,
        left_hand_data: Optional[Dict],
        right_hand_data: Optional[Dict],
        score: int,
        lives: int,
        difficulty: str
    ):
        """
        Log when a missile reaches the bottom without being shot.

        Args:
            target_finger: The finger that should have been pressed
            left_hand_data: Full tracking data for left hand
            right_hand_data: Full tracking data for right hand
            score: Current score
            lives: Current lives
            difficulty: Current difficulty level
        """
        if not self.session_data:
            return

        current_time = time.time()
        elapsed = current_time - self.session_start_time

        event = {
            "type": "missile_missed",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "target_finger": target_finger,
            "game_state": {
                "score": score,
                "lives": lives,
                "difficulty": difficulty or "N/A",
            },
            "hand_tracking": {
                "left_hand": self._extract_hand_data(left_hand_data),
                "right_hand": self._extract_hand_data(right_hand_data),
            }
        }

        self.session_data["events"].append(event)
        self.session_data["summary"]["missiles_missed"] += 1

        self._save_session()

    def log_hand_position(
        self,
        left_hand_data: Optional[Dict],
        right_hand_data: Optional[Dict]
    ):
        """
        Log periodic hand position snapshot (for continuous tracking).

        Args:
            left_hand_data: Full tracking data for left hand
            right_hand_data: Full tracking data for right hand
        """
        if not self.session_data:
            return

        current_time = time.time()
        elapsed = current_time - self.session_start_time

        event = {
            "type": "hand_position",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "hand_tracking": {
                "left_hand": self._extract_hand_data(left_hand_data),
                "right_hand": self._extract_hand_data(right_hand_data),
            }
        }

        self.session_data["events"].append(event)
        # Don't save on every position update to avoid performance issues
        # Will be saved on next finger press or end session

    def _extract_hand_data(self, hand_data: Optional[Dict]) -> Optional[Dict]:
        """Extract relevant tracking data from hand data."""
        if hand_data is None:
            return None

        extracted = {
            "palm_position": {
                "x": round(hand_data["palm_position"][0], 2),
                "y": round(hand_data["palm_position"][1], 2),
                "z": round(hand_data["palm_position"][2], 2),
            },
            "fingers": {}
        }

        for finger_name, finger_data in hand_data.get("fingers", {}).items():
            tip_pos = finger_data.get("tip_position", (0, 0, 0))
            extracted["fingers"][finger_name] = {
                "tip_position": {
                    "x": round(tip_pos[0], 2),
                    "y": round(tip_pos[1], 2),
                    "z": round(tip_pos[2], 2),
                },
                "extended": finger_data.get("extended", False),
            }

        return extracted

    def end_session(self, final_score: int, final_lives: int, duration_seconds: float = 0):
        """
        End the current session and save final data.

        Args:
            final_score: Final game score
            final_lives: Remaining lives
            duration_seconds: The total duration of the session in seconds
        """
        if not self.session_data:
            return

        end_time = time.time()
        self.session_data["end_time"] = datetime.now().isoformat()
        self.session_data["end_timestamp"] = end_time
        self.session_data["duration_seconds"] = round(duration_seconds, 2)
        self.session_data["final_score"] = final_score
        self.session_data["final_lives"] = final_lives

        self._save_session()
        print(f"Session ended. Log saved to: {self.session_file}")
        print(f"  Total presses: {self.session_data['summary']['total_presses']}")
        print(f"  Accuracy: {self.session_data['summary']['accuracy']}%")

        # Reset for next session
        self.session_id = None
        self.session_file = None
        self.session_data = None

    def _save_session(self):
        """Save session data to file."""
        if not self.session_file or not self.session_data:
            return

        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except IOError as e:
            print(f"Error saving session log: {e}")

    def get_session_file(self) -> Optional[str]:
        """Get the current session file path."""
        return self.session_file
