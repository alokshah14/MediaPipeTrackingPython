"""Leap Motion controller interface using official Python bindings."""

import time
import threading
from typing import Dict, Tuple

try:
    import leap
    LEAP_AVAILABLE = True
except ImportError:
    LEAP_AVAILABLE = False
    print("Warning: Leap Motion SDK not found. Running in simulation mode.")


class LeapListener(leap.Listener):
    """Listener for Leap Motion events."""

    def __init__(self, controller):
        """Initialize listener with reference to controller."""
        self.controller = controller

    def on_connection_event(self, event):
        """Handle connection event."""
        self.controller._on_connected()

    def on_device_event(self, event):
        """Handle device detection event."""
        self.controller._on_device(event)

    def on_tracking_event(self, event):
        """Handle tracking frame event."""
        self.controller._on_tracking(event)


class LeapController:
    """Interface for Leap Motion hand tracking using official bindings."""

    def __init__(self):
        """Initialize the Leap Motion controller."""
        self.connection = None
        self.listener = None
        self.connected = False
        self.has_device = False
        self.simulation_mode = not LEAP_AVAILABLE
        self._context_manager = None

        # Hand data storage
        self.hands_data = {'left': None, 'right': None}
        self._lock = threading.Lock()

        # Frame tracking
        self.last_frame_id = 0
        self.last_update_time = 0

        if LEAP_AVAILABLE:
            self._init_leap()

    def _init_leap(self):
        """Initialize the Leap Motion connection."""
        try:
            self.listener = LeapListener(self)
            self.connection = leap.Connection()
            self.connection.add_listener(self.listener)
            # Open the connection and keep it open
            self._context_manager = self.connection.open()
            self._context_manager.__enter__()
            self.connection.set_tracking_mode(leap.TrackingMode.Desktop)
            print("Leap Motion connection opened.")

            # Wait briefly to see if we get any tracking data
            import time
            time.sleep(0.3)
            if not self.has_device and not self.has_recent_data(max_age=1.0):
                print("No Leap Motion device detected. Falling back to simulation mode.")
                self.simulation_mode = True
        except Exception as e:
            print(f"Failed to connect to Leap Motion: {e}")
            self.simulation_mode = True

    def _on_connected(self):
        """Handle connection established."""
        self.connected = True
        print("Leap Motion connected successfully.")

    def _on_device(self, event):
        """Handle device detection."""
        self.has_device = True
        print("Leap Motion device detected.")

    def _on_tracking(self, event):
        """Handle tracking frame data."""
        with self._lock:
            self.last_frame_id = event.tracking_frame_id
            self.last_update_time = time.time()
            self._process_frame(event)

    def _process_frame(self, event):
        """Process a tracking frame and extract hand data."""
        new_hands = {'left': None, 'right': None}

        for hand in event.hands:
            hand_type = 'left' if str(hand.type) == "HandType.Left" else 'right'

            # Extract finger data
            fingers = {}
            finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']

            for i, digit in enumerate(hand.digits):
                finger_name = finger_names[i]
                tip = digit.distal.next_joint

                # Extract bone directions for angle calculation
                # Proximal bone direction
                proximal = digit.proximal
                proximal_dir = (proximal.next_joint.x - proximal.prev_joint.x,
                               proximal.next_joint.y - proximal.prev_joint.y,
                               proximal.next_joint.z - proximal.prev_joint.z)

                # Intermediate bone direction (or distal for thumb)
                if finger_name == 'thumb':
                    # Thumb uses distal bone
                    intermediate = digit.distal
                else:
                    intermediate = digit.intermediate
                intermediate_dir = (intermediate.next_joint.x - intermediate.prev_joint.x,
                                   intermediate.next_joint.y - intermediate.prev_joint.y,
                                   intermediate.next_joint.z - intermediate.prev_joint.z)

                # Extract full bone geometry for 3D rendering
                bones = {}
                bone_names = ['metacarpal', 'proximal', 'intermediate', 'distal']
                bone_objects = [digit.metacarpal, digit.proximal, digit.intermediate, digit.distal]
                for bone_name, bone in zip(bone_names, bone_objects):
                    bones[bone_name] = {
                        'start': (bone.prev_joint.x, bone.prev_joint.y, bone.prev_joint.z),
                        'end': (bone.next_joint.x, bone.next_joint.y, bone.next_joint.z),
                    }

                fingers[finger_name] = {
                    'tip_position': (tip.x, tip.y, tip.z),
                    'extended': digit.is_extended,
                    'proximal_direction': proximal_dir,
                    'intermediate_direction': intermediate_dir,
                    'bones': bones,
                    'valid': True,
                }

            palm = hand.palm

            new_hands[hand_type] = {
                'visible': True,
                'valid': True,
                'palm_position': (palm.position.x, palm.position.y, palm.position.z),
                'palm_normal': (palm.normal.x, palm.normal.y, palm.normal.z),
                'fingers': fingers,
                'grab_strength': hand.grab_strength,
                'pinch_strength': hand.pinch_strength,
            }

        self.hands_data = new_hands

    def update(self) -> Dict:
        """
        Get the current hand tracking data.

        Returns:
            Dictionary containing hand data for left and right hands
        """
        if self.simulation_mode:
            return {'left': None, 'right': None}

        with self._lock:
            return {'left': self.hands_data.get('left'), 'right': self.hands_data.get('right')}

    def get_hands_visible(self) -> Tuple[bool, bool]:
        """Check if hands are currently visible."""
        with self._lock:
            left_visible = self.hands_data['left'] is not None
            right_visible = self.hands_data['right'] is not None
        return left_visible, right_visible

    def is_connected(self) -> bool:
        """Check if Leap Motion is connected."""
        return self.connected and not self.simulation_mode

    def has_recent_data(self, max_age: float = 0.5) -> bool:
        """Check if we have recent tracking data."""
        return (time.time() - self.last_update_time) < max_age

    def cleanup(self):
        """Clean up the Leap Motion connection."""
        if self._context_manager:
            try:
                self._context_manager.__exit__(None, None, None)
            except:
                pass


class SimulatedLeapController(LeapController):
    """Simulated Leap controller that uses keyboard input for testing."""

    def __init__(self):
        """Initialize simulated controller."""
        self.connection = None
        self.connected = False
        self.simulation_mode = True
        self.hands_data = {'left': None, 'right': None}
        self._lock = threading.Lock()
        self.last_update_time = time.time()
        self._context_manager = None

        self.simulated_hands_visible = True
        self.simulated_finger_states = {
            'left_pinky': False, 'left_ring': False, 'left_middle': False,
            'left_index': False, 'left_thumb': False,
            'right_thumb': False, 'right_index': False, 'right_middle': False,
            'right_ring': False, 'right_pinky': False,
        }

        self.base_palm_y = 150.0
        self.base_finger_y = 200.0

        # Initialize simulated hands
        self._update_simulated_hands()

    def set_hands_visible(self, visible: bool):
        """Set whether hands are visible in simulation."""
        self.simulated_hands_visible = visible
        self._update_simulated_hands()

    def set_finger_pressed(self, finger_name: str, pressed: bool):
        """Simulate a finger press."""
        if finger_name in self.simulated_finger_states:
            self.simulated_finger_states[finger_name] = pressed
            self._update_simulated_hands()

    def _update_simulated_hands(self):
        """Update simulated hand data based on finger states."""
        self.last_update_time = time.time()

        if not self.simulated_hands_visible:
            self.hands_data = {'left': None, 'right': None}
            return

        import math

        for hand_type in ['left', 'right']:
            fingers = {}
            finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']
            # X offsets for each finger from palm center
            finger_x_offsets = {'thumb': 40, 'index': 20, 'middle': 0, 'ring': -20, 'pinky': -40}
            if hand_type == 'right':
                finger_x_offsets = {k: -v for k, v in finger_x_offsets.items()}

            palm_x = -100 if hand_type == 'left' else 100

            for finger_name in finger_names:
                key = f"{hand_type}_{finger_name}"
                is_pressed = self.simulated_finger_states.get(key, False)

                finger_x = palm_x + finger_x_offsets[finger_name]
                base_y = self.base_palm_y

                # Simulate bone directions - when pressed, angle between bones is ~45 degrees
                # When relaxed, bones are roughly aligned (angle ~0)
                if is_pressed:
                    proximal_dir = (0.0, 1.0, 0.0)
                    angle_rad = math.radians(45)
                    intermediate_dir = (0.0, math.cos(angle_rad), math.sin(angle_rad))
                else:
                    proximal_dir = (0.0, 1.0, 0.0)
                    intermediate_dir = (0.0, 1.0, 0.1)

                # Generate simulated bone positions
                bone_length = 25.0
                bones = {}
                # Metacarpal: from palm
                bones['metacarpal'] = {
                    'start': (finger_x, base_y, 0),
                    'end': (finger_x, base_y + bone_length, 0),
                }
                # Proximal
                bones['proximal'] = {
                    'start': (finger_x, base_y + bone_length, 0),
                    'end': (finger_x, base_y + bone_length * 2, 0),
                }
                # Intermediate - bends when pressed
                bend_y = bone_length * 0.7 if is_pressed else bone_length
                bend_z = bone_length * 0.7 if is_pressed else 0
                bones['intermediate'] = {
                    'start': (finger_x, base_y + bone_length * 2, 0),
                    'end': (finger_x, base_y + bone_length * 2 + bend_y, bend_z),
                }
                # Distal
                bones['distal'] = {
                    'start': bones['intermediate']['end'],
                    'end': (finger_x, bones['intermediate']['end'][1] + bone_length * 0.5,
                           bones['intermediate']['end'][2] + (bone_length * 0.3 if is_pressed else 0)),
                }

                tip_pos = bones['distal']['end']

                fingers[finger_name] = {
                    'tip_position': tip_pos,
                    'extended': not is_pressed,
                    'proximal_direction': proximal_dir,
                    'intermediate_direction': intermediate_dir,
                    'bones': bones,
                    'valid': True,
                }

            self.hands_data[hand_type] = {
                'visible': True,
                'valid': True,
                'palm_position': (palm_x, self.base_palm_y, 0.0),
                'palm_normal': (0.0, -1.0, 0.0),
                'fingers': fingers,
                'grab_strength': 0.0,
                'pinch_strength': 0.0,
            }

    def update(self) -> Dict:
        """Update and return simulated hand data."""
        if not self.simulated_hands_visible:
            return {'left': None, 'right': None}
        return {'left': self.hands_data.get('left'), 'right': self.hands_data.get('right')}

    def has_recent_data(self, max_age: float = 0.5) -> bool:
        """Always return True for simulation if hands visible."""
        return self.simulated_hands_visible

    def cleanup(self):
        """No cleanup needed for simulation."""
        pass
