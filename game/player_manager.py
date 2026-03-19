import json
import os
from datetime import datetime, date
from typing import Optional, Dict, List

PLAYERS_DIR = "data/players"
LAB_REQUIRED_GAMES = {'finger_invaders', 'egg_catcher', 'ping_pong'}

# Legacy single-file path — used for one-time migration only
_LEGACY_CONFIG_FILE = "data/player_config.json"


def _player_config_path(name: str) -> str:
    return os.path.join(PLAYERS_DIR, name, "config.json")


class PlayerManager:
    """Manages player identity and longitudinal study tracking (Lab vs. Home)."""

    def __init__(self):
        self.player_name = "Default_Player"
        self.home_start_date: Optional[date] = None
        self.is_home_study = False
        self.game_playtime_seconds: Dict[str, float] = {}
        self.lab_games_completed: List[str] = []
        self.lab_session_scores: Dict[str, int] = {}
        self._migrate_legacy_config()
        self._load_config()

    def _migrate_legacy_config(self):
        """One-time migration: move old single config.json into per-player directory."""
        if not os.path.exists(_LEGACY_CONFIG_FILE):
            return
        try:
            with open(_LEGACY_CONFIG_FILE, 'r') as f:
                data = json.load(f)
            name = data.get("player_name", "Default_Player").strip().replace(" ", "_")
            dest = _player_config_path(name)
            if not os.path.exists(dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Migrated legacy config to {dest}")
            os.rename(_LEGACY_CONFIG_FILE, _LEGACY_CONFIG_FILE + ".migrated")
        except Exception as e:
            print(f"Legacy config migration failed (non-fatal): {e}")

    def _load_config(self):
        """Load player configuration from disk for the current player_name."""
        path = _player_config_path(self.player_name)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.player_name = data.get("player_name", self.player_name)
                    start_date_str = data.get("home_start_date")
                    if start_date_str:
                        self.home_start_date = date.fromisoformat(start_date_str)
                    self.is_home_study = data.get("is_home_study", False)
                    self.game_playtime_seconds = data.get("game_playtime_seconds", {})
                    self.lab_games_completed = data.get("lab_games_completed", [])
                    self.lab_session_scores = data.get("lab_session_scores", {})
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading player config: {e}")
        else:
            # New player — reset to fresh state
            self.home_start_date = None
            self.is_home_study = False
            self.game_playtime_seconds = {}
            self.lab_games_completed = []
            self.lab_session_scores = {}

    def save_config(self):
        """Save current player configuration to disk."""
        path = _player_config_path(self.player_name)
        data = {
            "player_name": self.player_name,
            "home_start_date": self.home_start_date.isoformat() if self.home_start_date else None,
            "is_home_study": self.is_home_study,
            "game_playtime_seconds": self.game_playtime_seconds,
            "lab_games_completed": self.lab_games_completed,
            "lab_session_scores": self.lab_session_scores,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving player config: {e}")

    def load_player(self, name: str):
        """Switch to a different player (or create new). Saves current player first."""
        if not name or not name.strip():
            return
        new_name = name.strip().replace(" ", "_")
        if new_name == self.player_name:
            return  # Already this player
        self.save_config()  # Save old player's data
        self.player_name = new_name
        self._load_config()  # Load (or init fresh) new player's data
        print(f"Switched to player: {self.player_name}")

    def set_player_name(self, name: str):
        """Update player name — switches to that player's data (or creates fresh)."""
        self.load_player(name)

    def list_players(self) -> List[str]:
        """Return a list of all known player names."""
        if not os.path.isdir(PLAYERS_DIR):
            return []
        return [d for d in os.listdir(PLAYERS_DIR)
                if os.path.isdir(os.path.join(PLAYERS_DIR, d))]

    def record_lab_game(self, game_mode_value: str, score: int):
        if game_mode_value not in self.lab_games_completed:
            self.lab_games_completed.append(game_mode_value)
        self.lab_session_scores[game_mode_value] = score
        self.save_config()

    def is_lab_session_complete(self) -> bool:
        return LAB_REQUIRED_GAMES.issubset(set(self.lab_games_completed))

    def reset_lab_session(self):
        self.lab_games_completed = []
        self.lab_session_scores = {}
        self.save_config()

    def start_home_study(self):
        self.home_start_date = datetime.now().date()
        self.is_home_study = True
        self.save_config()

    def add_game_playtime(self, game_mode_value: str, seconds: float):
        if seconds <= 0:
            return
        self.game_playtime_seconds[game_mode_value] = (
            self.game_playtime_seconds.get(game_mode_value, 0.0) + seconds
        )
        self.save_config()

    def get_playtime_display(self) -> Dict[str, str]:
        result = {}
        for key, total_secs in self.game_playtime_seconds.items():
            mins = int(total_secs) // 60
            secs = int(total_secs) % 60
            result[key] = f"{mins}m {secs:02d}s"
        return result

    def get_days_since_start(self) -> int:
        if not self.home_start_date:
            return 0
        delta = datetime.now().date() - self.home_start_date
        return delta.days

    def get_study_status_text(self) -> str:
        if not self.is_home_study:
            return "Mode: Lab Session"
        days = self.get_days_since_start()
        if days < 7:
            return f"Home Study: Day {days + 1} (Week 1 - Fixed Order)"
        else:
            return f"Home Study: Day {days + 1} (Week {days // 7 + 1} - Random Order)"
