import json
import os
from datetime import datetime, date
from typing import Optional, Dict

PLAYER_CONFIG_FILE = "data/player_config.json"

class PlayerManager:
    """Manages player identity and longitudinal study tracking (Lab vs. Home)."""

    def __init__(self):
        self.player_name = "Default_Player"
        self.home_start_date: Optional[date] = None
        self.is_home_study = False
        # Cumulative playtime in seconds per game mode (key = GameMode.value string)
        self.game_playtime_seconds: Dict[str, float] = {}
        self._load_config()

    def _load_config(self):
        """Load player configuration from disk."""
        if os.path.exists(PLAYER_CONFIG_FILE):
            try:
                with open(PLAYER_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.player_name = data.get("player_name", "Default_Player")
                    start_date_str = data.get("home_start_date")
                    if start_date_str:
                        self.home_start_date = date.fromisoformat(start_date_str)
                    self.is_home_study = data.get("is_home_study", False)
                    self.game_playtime_seconds = data.get("game_playtime_seconds", {})
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error loading player config: {e}")

    def save_config(self):
        """Save current player configuration to disk."""
        data = {
            "player_name": self.player_name,
            "home_start_date": self.home_start_date.isoformat() if self.home_start_date else None,
            "is_home_study": self.is_home_study,
            "game_playtime_seconds": self.game_playtime_seconds,
        }
        os.makedirs(os.path.dirname(PLAYER_CONFIG_FILE), exist_ok=True)
        try:
            with open(PLAYER_CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving player config: {e}")

    def set_player_name(self, name: str):
        """Update the player name and save."""
        if name and name.strip():
            self.player_name = name.strip().replace(" ", "_")
            self.save_config()

    def start_home_study(self):
        """Mark the beginning of the home study period."""
        self.home_start_date = datetime.now().date()
        self.is_home_study = True
        self.save_config()

    def add_game_playtime(self, game_mode_value: str, seconds: float):
        """Accumulate playtime for a specific game mode and persist it."""
        if seconds <= 0:
            return
        self.game_playtime_seconds[game_mode_value] = (
            self.game_playtime_seconds.get(game_mode_value, 0.0) + seconds
        )
        self.save_config()

    def get_playtime_display(self) -> Dict[str, str]:
        """Return a dict of game_mode_value -> human-readable playtime string."""
        result = {}
        for key, total_secs in self.game_playtime_seconds.items():
            mins = int(total_secs) // 60
            secs = int(total_secs) % 60
            result[key] = f"{mins}m {secs:02d}s"
        return result

    def get_days_since_start(self) -> int:
        """Calculate number of days since the home study started."""
        if not self.home_start_date:
            return 0
        delta = datetime.now().date() - self.home_start_date
        return delta.days

    def get_study_status_text(self) -> str:
        """Get a string describing the current study progress."""
        if not self.is_home_study:
            return "Mode: Lab Session"

        days = self.get_days_since_start()
        if days < 7:
            return f"Home Study: Day {days + 1} (Week 1 - Fixed Order)"
        else:
            return f"Home Study: Day {days + 1} (Week {days // 7 + 1} - Random Order)"
