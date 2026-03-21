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

    def __init__(self, log_directory: str = None):
        if log_directory is None:
            from game.constants import DATA_DIR
            log_directory = os.path.join(DATA_DIR, "session_logs")
        """
        Initialize the session logger.

        Args:
            log_directory: Base directory to store session log files
        """
        self.base_log_directory = self._resolve_log_directory(log_directory)
        self.player_name = "Default_Player"
        self.log_directory = os.path.join(self.base_log_directory, self.player_name)
        
        self.session_id = None
        self.session_file = None
        self.session_data = None
        self.session_start_time = None

        # Ensure log directory exists
        os.makedirs(self.log_directory, exist_ok=True)

    def set_player_name(self, player_name: str):
        """Update the player name and adjust log directory."""
        if player_name:
            self.player_name = player_name
            self.log_directory = os.path.join(self.base_log_directory, self.player_name)
            os.makedirs(self.log_directory, exist_ok=True)

    def _resolve_log_directory(self, log_directory: str) -> str:
        """Resolve log directory relative to repo root when a relative path is used."""
        if os.path.isabs(log_directory):
            return log_directory

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(base_dir, log_directory)

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
            "player_name": self.player_name,
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
        print(f"Session logging started for {self.player_name}: {self.session_file}")

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
        """Log a finger press event."""
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

        if trial_metrics:
            event["biomechanics"] = {
                "reaction_time_ms": round(trial_metrics.reaction_time_ms, 2),
                "reaction_time_from_zone_ms": round(trial_metrics.reaction_time_from_zone_ms, 2),
                "reaction_time_from_appear_ms": round(trial_metrics.reaction_time_from_appear_ms, 2),
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

        self.session_data["summary"]["total_presses"] += 1
        if is_correct:
            self.session_data["summary"]["correct_presses"] += 1
        else:
            self.session_data["summary"]["wrong_presses"] += 1

        total = self.session_data["summary"]["total_presses"]
        correct = self.session_data["summary"]["correct_presses"]
        self.session_data["summary"]["accuracy"] = round(correct / total * 100, 2)

        if trial_metrics:
            if trial_metrics.is_clean_trial:
                self.session_data["summary"]["clean_trials"] += 1
            if trial_metrics.coupled_keypress:
                self.session_data["summary"]["coupled_keypresses"] += 1

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
        """Log missed missile."""
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
        """Log hand position snapshot."""
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

    def _extract_hand_data(self, hand_data: Optional[Dict]) -> Optional[Dict]:
        """Extract relevant tracking data from hand data."""
        if hand_data is None: return None
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
                    "x": round(tip_pos[0], 2), "y": round(tip_pos[1], 2), "z": round(tip_pos[2], 2),
                },
                "extended": finger_data.get("extended", False),
            }
        return extracted

    def end_session(self, final_score: int, final_lives: int, duration_seconds: float = 0):
        """End session and save final data."""
        if not self.session_data: return
        self.session_data["end_time"] = datetime.now().isoformat()
        self.session_data["end_timestamp"] = time.time()
        self.session_data["duration_seconds"] = round(duration_seconds, 2)
        self.session_data["final_score"] = final_score
        self.session_data["final_lives"] = final_lives
        self._save_session()
        self.session_data = None

    def _save_session(self):
        """Save session data to file."""
        if not self.session_file or not self.session_data: return
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
        except IOError as e:
            print(f"Error saving session log: {e}")

    def log_calibration(self, calibration_data: Dict):
        """Log a standalone calibration event."""
        self.session_id = datetime.now().strftime("cal_%Y%m%d_%H%M%S")
        self.session_file = os.path.join(
            self.log_directory,
            f"calibration_{self.session_id}.json"
        )
        data = {
            "session_id": self.session_id,
            "player_name": self.player_name,
            "timestamp": datetime.now().isoformat(),
            "type": "calibration_only",
            "calibration_data": calibration_data
        }
        try:
            with open(self.session_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Calibration log saved for {self.player_name}: {self.session_file}")
        except IOError as e:
            print(f"Error saving calibration log: {e}")
        self.session_id = None
        self.session_file = None

    def get_session_file(self) -> Optional[str]:
        return self.session_file
