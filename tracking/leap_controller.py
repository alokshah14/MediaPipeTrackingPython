"""Leap Motion controller interface using official Python bindings, with MediaPipe fallback."""

import time
import threading
from typing import Dict, Tuple
import os

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    mp = None
    python = None
    vision = None
    MEDIAPIPE_AVAILABLE = False

def _maybe_add_leap_paths():
    """Add likely Leap SDK Python binding paths to sys.path."""
    import os
    import sys

    roots = []
    for env_var in ("LEAPSDK_INSTALL_LOCATION", "LEAP_SDK_PATH"):
        val = os.environ.get(env_var)
        if val:
            roots.append(val)

    candidates = []
    for root in roots:
        candidates.extend([
            os.path.join(root, "leapc_cffi", "python"),
            os.path.join(root, "leapc_cffi"),
            os.path.join(root, "python"),
        ])

    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
            print(f"Added Leap SDK path to sys.path: {path}")

    # Ensure LeapC.dll search path is set when running on Windows
    if os.name == "nt":
        for root in roots:
            leapc_dir = os.path.join(root, "leapc_cffi")
            if os.path.isdir(leapc_dir):
                try:
                    os.add_dll_directory(leapc_dir)
                    print(f"Added LeapC.dll search path: {leapc_dir}")
                except Exception as e:
                    print(f"Failed to add LeapC.dll search path: {leapc_dir} ({e})")


def _load_leap_from_sdk():
    """Try to load leap.py directly from the SDK bundle."""
    import importlib.util
    import os
    import sys

    roots = []
    for env_var in ("LEAPSDK_INSTALL_LOCATION", "LEAP_SDK_PATH"):
        val = os.environ.get(env_var)
        if val:
            roots.append(val)

    candidates = []
    for root in roots:
        candidates.append(os.path.join(root, "leapc_cffi", "leap.py"))
        candidates.append(os.path.join(root, "leapc_cffi", "leap", "__init__.py"))
        candidates.append(os.path.join(root, "leap.py"))
        candidates.append(os.path.join(root, "leap", "__init__.py"))

    if candidates:
        print("Leap SDK candidate files:")
        for c in candidates:
            print(f"  {c} {'(exists)' if os.path.isfile(c) else ''}")

    for path in candidates:
        if os.path.isfile(path):
            try:
                spec = importlib.util.spec_from_file_location("leap", path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    sys.modules["leap"] = module
                    print(f"Loaded leap.py directly from: {path}")
                    return module
            except Exception as e:
                print(f"Failed to load leap.py from {path}: {e}")
    if roots:
        print(f"No leap module file found under: {roots}")
    return None


listener_base = None
leap = None

try:
    _maybe_add_leap_paths()
    # Prefer the installed bindings (bundled by PyInstaller), then fall back to SDK file.
    try:
        import leap as _leap_mod
        leap = _leap_mod
    except Exception as e:
        print(f"Failed to import bundled leap module: {e}")
    if leap is None:
        leap = _load_leap_from_sdk()
    if leap is None:
        import leap

    def _get_listener_base(module):
        return getattr(module, "Listener", None) or getattr(module, "EventListener", None)

    listener_base = _get_listener_base(leap)
    LEAP_AVAILABLE = listener_base is not None and hasattr(leap, "Connection")
    try:
        print(f"Leap module loaded from: {getattr(leap, '__file__', '<builtin>')}")
        print(f"Leap API available: {LEAP_AVAILABLE}")
        print(f"Leap has Listener: {hasattr(leap, 'Listener')}, EventListener: {hasattr(leap, 'EventListener')}, Connection: {hasattr(leap, 'Connection')}")
        listener_like = [n for n in dir(leap) if "Listener" in n]
        if listener_like:
            print(f"Leap listener-like symbols: {listener_like}")
    except Exception:
        pass

    if not LEAP_AVAILABLE:
        print("Warning: Leap SDK Python bindings not found or incompatible. Running in simulation mode.")
except Exception as e:
    LEAP_AVAILABLE = False
    print(f"Warning: Leap Motion SDK not available ({e}). Running without Leap support.")


if LEAP_AVAILABLE:
    class LeapListener(listener_base):
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
else:
    # Dummy listener for when leap is not available
    class LeapListener:
        def __init__(self, controller):
            pass


class LeapController:
    """Interface for hand tracking, preferring Leap Motion with MediaPipe fallback."""

    def __init__(self, prefer_mediapipe: bool = False):
        """Initialize the Leap Motion controller."""
        self.connection = None
        self.listener = None
        self.connected = False
        self.has_device = False
        self.prefer_mediapipe = prefer_mediapipe
        self.tracking_mode = 'simulation'
        self.simulation_mode = True
        self._context_manager = None
        self.connection_failed = False

        self.mp_hands = None
        self.cap = None
        self._running = True
        self._mp_thread = None
        self._leap_thread = None

        # Hand data storage
        self.hands_data = {'left': None, 'right': None}
        self._lock = threading.Lock()

        # Frame tracking
        self.last_frame_id = 0
        self.last_update_time = 0

        if prefer_mediapipe and MEDIAPIPE_AVAILABLE:
            self._init_mediapipe()
        elif LEAP_AVAILABLE:
            self._init_leap()
        elif MEDIAPIPE_AVAILABLE:
            self._init_mediapipe()

    def _init_leap(self):
        """Initialize the Leap Motion connection."""
        try:
            self.tracking_mode = 'leap'
            self.simulation_mode = False
            self.listener = LeapListener(self)
            self.connection = leap.Connection()
            self.connection.add_listener(self.listener)
            # Open the connection and keep it open
            self._context_manager = self.connection.open()
            self._context_manager.__enter__()
            
            # Set desktop mode
            try:
                self.connection.set_tracking_mode(leap.TrackingMode.Desktop)
            except:
                # Older versions might use a different way to set tracking mode
                pass
            
            # Start a background thread to poll the connection
            self._running = True
            self._leap_thread = threading.Thread(target=self._leap_poll_loop, daemon=True)
            self._leap_thread.start()
            
            print("Leap Motion connection opened.")

            # Wait briefly to see if we get any tracking data
            import time
            time.sleep(1.0)
            if not self.has_device and not self.has_recent_data(max_age=1.5):
                print("No Leap Motion device detected.")
                # Fall back to MediaPipe if no device found
                self._cleanup_leap_resources()
                if MEDIAPIPE_AVAILABLE:
                    print("Defaulting to MediaPipe via webcam...")
                    self._init_mediapipe()
                else:
                    print("MediaPipe not available, falling back to simulation.")
                    self.tracking_mode = 'simulation'
                    self.simulation_mode = True
        except Exception as e:
            print(f"Failed to connect to Leap Motion: {e}")
            self.connection_failed = True
            self._cleanup_leap_resources()
            if MEDIAPIPE_AVAILABLE:
                print("Defaulting to MediaPipe via webcam...")
                self._init_mediapipe()
            else:
                print("MediaPipe not available, falling back to simulation.")
                self.tracking_mode = 'simulation'
                self.simulation_mode = True

    def _init_mediapipe(self):
        """Initialize MediaPipe hand tracking."""
        if not MEDIAPIPE_AVAILABLE or cv2 is None:
            self.tracking_mode = 'simulation'
            self.simulation_mode = True
            return

        try:
            model_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'models', 'hand_landmarker.task'))
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"MediaPipe model not found at {model_path}")

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
            )
            self.mp_hands = vision.HandLandmarker.create_from_options(options)
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Could not open webcam")

            self.tracking_mode = 'mediapipe'
            self.simulation_mode = False
            self._running = True
            self._mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
            self._mp_thread.start()
            print("MediaPipe hand tracking initialized with webcam.")
        except Exception as e:
            print(f"Failed to initialize MediaPipe: {e}")
            self._cleanup_mediapipe_resources()
            self.tracking_mode = 'simulation'
            self.simulation_mode = True

    def _mediapipe_loop(self):
        """Continuously process webcam frames in the background."""
        while self._running and self.tracking_mode == 'mediapipe':
            self._process_mediapipe_frame()
            time.sleep(0.01)

    def _leap_poll_loop(self):
        """Continuously poll Leap Motion connection for events."""
        while self._running and self.tracking_mode == 'leap':
            if self.connection:
                try:
                    self.connection.poll(100) # 100ms timeout
                except Exception as e:
                    print(f"Leap poll error: {e}")
                    time.sleep(0.1)
            else:
                time.sleep(0.1)

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
            # Detect hand type robustly
            hand_type_str = str(hand.type)
            if "Left" in hand_type_str:
                hand_type = 'left'
            elif "Right" in hand_type_str:
                hand_type = 'right'
            else:
                # Fallback for integer or other formats
                hand_type = 'left' if int(hand.type) == 0 else 'right'

            # Extract finger data
            fingers = {}
            finger_names = ['thumb', 'index', 'middle', 'ring', 'pinky']

            for i, digit in enumerate(hand.digits):
                finger_name = finger_names[i]
                tip = digit.distal.next_joint

                # Extract bone directions for angle calculation
                metacarpal = digit.metacarpal
                metacarpal_dir = (metacarpal.next_joint.x - metacarpal.prev_joint.x,
                                  metacarpal.next_joint.y - metacarpal.prev_joint.y,
                                  metacarpal.next_joint.z - metacarpal.prev_joint.z)

                proximal = digit.proximal
                proximal_dir = (proximal.next_joint.x - proximal.prev_joint.x,
                               proximal.next_joint.y - proximal.prev_joint.y,
                               proximal.next_joint.z - proximal.prev_joint.z)

                if finger_name == 'thumb':
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
                    'metacarpal_direction': metacarpal_dir,
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
                'palm_normal': (0.0, -1.0, 0.0),
                'fingers': fingers,
                'grab_strength': hand.grab_strength,
                'pinch_strength': hand.pinch_strength,
                'confidence': getattr(hand, 'confidence', 1.0),
            }

        self.hands_data = new_hands

    def _process_mediapipe_frame(self):
        """Process a webcam frame using MediaPipe."""
        if not self.cap or not self.mp_hands or cv2 is None or mp is None:
            return

        success, image = self.cap.read()
        if not success:
            return

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        timestamp_ms = int(time.time() * 1000)
        results = self.mp_hands.detect_for_video(mp_image, timestamp_ms)

        new_hands = {'left': None, 'right': None}
        if results.hand_landmarks and results.handedness:
            for i, hand_landmarks in enumerate(results.hand_landmarks):
                handedness_list = results.handedness[i] if i < len(results.handedness) else []
                if handedness_list:
                    # MediaPipe labels are relative to the image. 
                    # Mirrored image: "Left" label -> user's actual right hand
                    # If user sees them as flipped, we swap.
                    label = handedness_list[0].category_name # "Left" or "Right"
                    hand_type = 'right' if label == 'Left' else 'left'
                else:
                    hand_type = 'right' if i == 0 else 'left'
                
                if hand_type in new_hands:
                    new_hands[hand_type] = self._convert_mediapipe_landmarks_to_hand_data(hand_landmarks)

        with self._lock:
            self.hands_data = new_hands
            self.last_update_time = time.time()

    def _convert_mediapipe_landmarks_to_hand_data(self, hand_landmarks):
        """Convert MediaPipe landmarks to the internal hand data structure."""
        scale_factor = 400.0
        # Center around landmark 9 (middle finger MCP) for more stable "palm center"
        cx, cy, cz = hand_landmarks[9].x, hand_landmarks[9].y, hand_landmarks[9].z
        
        landmark_points = [
            ((lm.x - cx) * scale_factor, 
             (cy - lm.y) * scale_factor + 150.0, 
             (cz - lm.z) * scale_factor)
            for lm in hand_landmarks
        ]
        
        finger_indices = {
            'thumb': [0, 1, 2, 3, 4],
            'index': [0, 5, 6, 7, 8],
            'middle': [0, 9, 10, 11, 12],
            'ring': [0, 13, 14, 15, 16],
            'pinky': [0, 17, 18, 19, 20],
        }

        fingers = {}
        for finger_name, indices in finger_indices.items():
            points = [landmark_points[i] for i in indices]
            metacarpal_dir = self._vector_subtract(points[1], points[0])
            proximal_dir = self._vector_subtract(points[2], points[1])
            intermediate_dir = self._vector_subtract(points[3], points[2])
            bones = {
                'metacarpal': {'start': points[0], 'end': points[1]},
                'proximal': {'start': points[1], 'end': points[2]},
                'intermediate': {'start': points[2], 'end': points[3]},
                'distal': {'start': points[3], 'end': points[4]},
            }
            fingers[finger_name] = {
                'tip_position': points[-1],
                'extended': True,
                'metacarpal_direction': metacarpal_dir,
                'proximal_direction': proximal_dir,
                'intermediate_direction': intermediate_dir,
                'bones': bones,
                'valid': True,
            }

        return {
            'visible': True,
            'valid': True,
            'palm_position': landmark_points[0],
            'palm_normal': (0, 0, 1),
            'fingers': fingers,
            'grab_strength': 0.0,
            'pinch_strength': 0.0,
            'confidence': 1.0,
        }

    def _vector_subtract(self, a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def update(self) -> Dict:
        """Get the current hand tracking data."""
        if self.tracking_mode == 'simulation':
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
        """Check if a non-simulated tracking source is connected."""
        if self.tracking_mode == 'leap':
            return self.connected
        if self.tracking_mode == 'mediapipe':
            return self.cap is not None and self.cap.isOpened()
        return False

    def has_recent_data(self, max_age: float = 0.5) -> bool:
        """Check if we have recent tracking data."""
        return (time.time() - self.last_update_time) < max_age

    def cleanup(self):
        """Clean up the active tracking backend."""
        self._running = False
        self._cleanup_leap_resources()
        self._cleanup_mediapipe_resources()

    def _cleanup_leap_resources(self):
        self._running = False
        try:
            if hasattr(self, '_leap_thread') and self._leap_thread:
                self._leap_thread.join(timeout=0.2)
        except:
            pass
            
        try:
            if self.connection and self.listener:
                self.connection.remove_listener(self.listener)
                self.listener = None
        except Exception as e:
            print(f"Error removing Leap listener: {e}")
        try:
            if self._context_manager:
                self._context_manager.__exit__(None, None, None)
                self._context_manager = None
        except Exception as e:
            print(f"Error closing Leap connection: {e}")
        self.connection = None
        self.connected = False

    def _cleanup_mediapipe_resources(self):
        try:
            if self.mp_hands:
                self.mp_hands.close()
                self.mp_hands = None
        except Exception as e:
            print(f"Error closing MediaPipe: {e}")
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
        except Exception as e:
            print(f"Error releasing webcam: {e}")


class SimulatedLeapController(LeapController):
    """Simulated Leap controller that uses keyboard input for testing."""

    def __init__(self):
        """Initialize simulated controller."""
        self.connection = None
        self.connected = False
        self.has_device = False
        self.prefer_mediapipe = False
        self.tracking_mode = 'simulation'
        self.simulation_mode = True
        self.hands_data = {'left': None, 'right': None}
        self._lock = threading.Lock()
        self.last_update_time = time.time()
        self._context_manager = None
        self.connection_failed = False
        self.mp_hands = None
        self.cap = None
        self._running = False
        self._mp_thread = None
        self._leap_thread = None

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

                metacarpal_dir = (0.0, 1.0, 0.0)
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
                    'metacarpal_direction': metacarpal_dir,
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
