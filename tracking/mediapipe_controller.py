"""MediaPipe hand tracking controller with keyboard simulation fallback."""

import os
import threading
import time
from typing import Dict, List, Tuple

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

try:
    from pygrabber.dshow_graph import FilterGraph
except ImportError:
    FilterGraph = None


class MediaPipeController:
    """Interface for webcam-based MediaPipe hand tracking."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.tracking_mode = "simulation"
        self.simulation_mode = True
        self.connected = False
        self.connection_failed = False
        self.mp_hands = None
        self.cap = None
        self._running = False
        self._mp_thread = None
        self.hands_data = {"left": None, "right": None}
        self._lock = threading.Lock()
        self.last_update_time = 0.0
        self.last_frame_id = 0
        self._init_mediapipe()

    @staticmethod
    def _candidate_backends() -> List[int | None]:
        """Return camera backends to try in order."""
        if cv2 is None:
            return [None]

        if os.name == "nt":
            backends: List[int | None] = []
            if hasattr(cv2, "CAP_DSHOW"):
                backends.append(cv2.CAP_DSHOW)
            if hasattr(cv2, "CAP_MSMF"):
                backends.append(cv2.CAP_MSMF)
            backends.append(None)
            return backends
        return [None]

    @classmethod
    def _create_capture(cls, camera_index: int):
        """Create a webcam capture, trying a few backends on Windows."""
        if cv2 is None:
            return None

        for backend in cls._candidate_backends():
            cap = None
            try:
                if backend is None:
                    cap = cv2.VideoCapture(camera_index)
                else:
                    cap = cv2.VideoCapture(camera_index, backend)
                if cap and cap.isOpened():
                    return cap
                if cap:
                    cap.release()
            except Exception:
                try:
                    if cap:
                        cap.release()
                except Exception:
                    pass
        return None

    @staticmethod
    def _wait_for_frame(cap, attempts: int = 8, delay_s: float = 0.12) -> bool:
        """Give a camera a brief warm-up window before treating it as dead."""
        if cap is None:
            return False

        for _ in range(attempts):
            ok, _ = cap.read()
            if ok:
                return True
            time.sleep(delay_s)
        return False

    @classmethod
    def list_available_cameras(cls, max_devices: int = 6) -> List[Dict[str, int | str]]:
        """Return a lightweight list of usable camera indices."""
        if cv2 is None:
            return []

        device_names: List[str] = []
        if os.name == "nt" and FilterGraph is not None:
            try:
                device_names = list(FilterGraph().get_input_devices())
            except Exception:
                device_names = []

        cameras = []
        for camera_index in range(max_devices):
            cap = None
            try:
                cap = cls._create_capture(camera_index)
                if cap and cap.isOpened():
                    if cls._wait_for_frame(cap):
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                        if camera_index < len(device_names) and device_names[camera_index]:
                            label = device_names[camera_index]
                        else:
                            label = f"Camera {camera_index}"
                        if width > 0 and height > 0:
                            label = f"{label} ({width}x{height})"
                        cameras.append({
                            "index": camera_index,
                            "label": label,
                        })
            except Exception:
                pass
            finally:
                try:
                    if cap:
                        cap.release()
                except Exception:
                    pass
        return cameras

    def _init_mediapipe(self):
        """Initialize MediaPipe hand tracking."""
        if not MEDIAPIPE_AVAILABLE or cv2 is None:
            print("MediaPipe dependencies are not available. Falling back to simulation.")
            self.tracking_mode = "simulation"
            self.simulation_mode = True
            self.connection_failed = True
            return

        try:
            model_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "models", "hand_landmarker.task")
            )
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"MediaPipe model not found at {model_path}")

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
            )
            self.mp_hands = vision.HandLandmarker.create_from_options(options)
            self.cap = self._create_capture(self.camera_index)
            if not self.cap or not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera {self.camera_index}")
            if not self._wait_for_frame(self.cap, attempts=10, delay_s=0.1):
                raise RuntimeError(f"Camera {self.camera_index} opened but did not produce frames")

            self.tracking_mode = "mediapipe"
            self.simulation_mode = False
            self.connected = True
            self._running = True
            self._mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
            self._mp_thread.start()
            print(f"MediaPipe hand tracking initialized with camera {self.camera_index}.")
        except Exception as e:
            print(f"Failed to initialize MediaPipe: {e}")
            self.connection_failed = True
            self._cleanup_mediapipe_resources()
            self.tracking_mode = "simulation"
            self.simulation_mode = True

    def _mediapipe_loop(self):
        """Continuously process webcam frames in the background."""
        while self._running and self.tracking_mode == "mediapipe":
            self._process_mediapipe_frame()
            time.sleep(0.01)

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

        new_hands = {"left": None, "right": None}
        if results.hand_landmarks and results.handedness:
            for i, hand_landmarks in enumerate(results.hand_landmarks):
                handedness_list = results.handedness[i] if i < len(results.handedness) else []
                if handedness_list:
                    label = handedness_list[0].category_name
                    hand_type = "right" if label == "Left" else "left"
                else:
                    hand_type = "right" if i == 0 else "left"

                if hand_type in new_hands:
                    new_hands[hand_type] = self._convert_mediapipe_landmarks_to_hand_data(hand_landmarks)

        with self._lock:
            self.hands_data = new_hands
            self.last_update_time = time.time()
            self.last_frame_id += 1

    def _convert_mediapipe_landmarks_to_hand_data(self, hand_landmarks):
        """Convert MediaPipe landmarks to the internal hand data structure."""
        scale_factor = 400.0
        cx, cy, cz = hand_landmarks[9].x, hand_landmarks[9].y, hand_landmarks[9].z

        landmark_points = [
            ((lm.x - cx) * scale_factor, (cy - lm.y) * scale_factor + 150.0, (cz - lm.z) * scale_factor)
            for lm in hand_landmarks
        ]

        finger_indices = {
            "thumb": [0, 1, 2, 3, 4],
            "index": [0, 5, 6, 7, 8],
            "middle": [0, 9, 10, 11, 12],
            "ring": [0, 13, 14, 15, 16],
            "pinky": [0, 17, 18, 19, 20],
        }

        fingers = {}
        for finger_name, indices in finger_indices.items():
            points = [landmark_points[i] for i in indices]
            bones = {
                "metacarpal": {"start": points[0], "end": points[1]},
                "proximal": {"start": points[1], "end": points[2]},
                "intermediate": {"start": points[2], "end": points[3]},
                "distal": {"start": points[3], "end": points[4]},
            }
            fingers[finger_name] = {
                "tip_position": points[-1],
                "extended": True,
                "metacarpal_direction": self._vector_subtract(points[1], points[0]),
                "proximal_direction": self._vector_subtract(points[2], points[1]),
                "intermediate_direction": self._vector_subtract(points[3], points[2]),
                "bones": bones,
                "valid": True,
            }

        return {
            "visible": True,
            "valid": True,
            "palm_position": landmark_points[0],
            "palm_normal": (0, 0, 1),
            "fingers": fingers,
            "grab_strength": 0.0,
            "pinch_strength": 0.0,
            "confidence": 1.0,
        }

    def _vector_subtract(self, a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def update(self) -> Dict:
        """Get the current hand tracking data."""
        if self.tracking_mode == "simulation":
            return {"left": None, "right": None}

        with self._lock:
            return {"left": self.hands_data.get("left"), "right": self.hands_data.get("right")}

    def get_hands_visible(self) -> Tuple[bool, bool]:
        """Check if hands are currently visible."""
        with self._lock:
            left_visible = self.hands_data["left"] is not None
            right_visible = self.hands_data["right"] is not None
        return left_visible, right_visible

    def is_connected(self) -> bool:
        """Check if the webcam tracking source is connected."""
        return self.cap is not None and self.cap.isOpened()

    def has_recent_data(self, max_age: float = 0.5) -> bool:
        """Check if we have recent tracking data."""
        return (time.time() - self.last_update_time) < max_age

    def cleanup(self):
        """Clean up the active tracking backend."""
        self._running = False
        try:
            if self._mp_thread:
                self._mp_thread.join(timeout=0.2)
        except Exception:
            pass
        self._cleanup_mediapipe_resources()

    def _cleanup_mediapipe_resources(self):
        self.connected = False
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


class SimulatedHandController(MediaPipeController):
    """Keyboard-based simulated hand controller for testing."""

    def __init__(self):
        self.tracking_mode = "simulation"
        self.simulation_mode = True
        self.connected = False
        self.connection_failed = False
        self.mp_hands = None
        self.cap = None
        self._running = False
        self._mp_thread = None
        self.hands_data = {"left": None, "right": None}
        self._lock = threading.Lock()
        self.last_update_time = time.time()
        self.last_frame_id = 0
        self.simulated_hands_visible = True
        self.simulated_finger_states = {
            "left_pinky": False,
            "left_ring": False,
            "left_middle": False,
            "left_index": False,
            "left_thumb": False,
            "right_thumb": False,
            "right_index": False,
            "right_middle": False,
            "right_ring": False,
            "right_pinky": False,
        }
        self.base_palm_y = 150.0
        self.base_finger_y = 200.0
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
