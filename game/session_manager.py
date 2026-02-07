import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from game.constants import GameMode, ALL_GAME_MODES


class SessionManager:
    SESSION_FILE = "data/session_data.json"
    DAILY_SESSIONS_COUNT = 5
    SESSION_DURATION_MINUTES = 5 # Each mini-game session duration
    DAILY_MINIMUM_PLAYTIME_MINUTES = 25 # Total minimum for structured sessions
    POST_STRUCTURED_MENU_OPTIONS = ["Calibrate", "Free Play", "High Scores", "Quit"]

    def __init__(self, is_test_mode: bool = False):
        self.is_test_mode = is_test_mode
        self.session_data = self._load_session_data()
        self.current_session_plan = None
        self._ensure_session_data_integrity()
        self.new_day_check() # Generate new plan if it's a new day

    def _load_session_data(self) -> Dict:
        """Loads session data from file or returns a default structure."""
        if os.path.exists(self.SESSION_FILE):
            try:
                with open(self.SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert string dates back to datetime objects
                    data['last_played_date'] = datetime.fromisoformat(data['last_played_date'])
                    for game_mode_str, session_info in data['game_performance'].items():
                        if 'last_played' in session_info and session_info['last_played']:
                            session_info['last_played'] = datetime.fromisoformat(session_info['last_played'])
                    return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading session data: {e}. Starting fresh.")
        return self._default_session_data()

    def _default_session_data(self) -> Dict:
        """Returns a new, default session data structure."""
        return {
            "last_played_date": datetime.min, # epoch start to force new day on first run
            "total_playtime_seconds": 0,
            "sessions_today": 0,
            "structured_sessions_completed_today": 0,
            "last_session_number": 0,
            "game_performance": {mode.value: {"score_history": [], "last_played": None, "avg_score": 0, "play_count": 0} for mode in ALL_GAME_MODES},
            "current_session_plan": None # Stored as dict for JSON compatibility
        }

    def _save_session_data(self):
        """Saves current session data to file."""
        try:
            # Convert datetime objects to ISO format strings for JSON
            savable_data = self.session_data.copy()
            savable_data['last_played_date'] = savable_data['last_played_date'].isoformat()
            
            game_perf_savable = {}
            for game_mode_str, session_info in savable_data['game_performance'].items():
                game_perf_savable[game_mode_str] = session_info.copy()
                if game_perf_savable[game_mode_str]['last_played']:
                    game_perf_savable[game_mode_str]['last_played'] = game_perf_savable[game_mode_str]['last_played'].isoformat()
            savable_data['game_performance'] = game_perf_savable

            # Ensure data/ directory exists
            os.makedirs(os.path.dirname(self.SESSION_FILE), exist_ok=True)

            with open(self.SESSION_FILE, 'w') as f:
                json.dump(savable_data, f, indent=2)
        except IOError as e:
            print(f"Error saving session data: {e}")

    def _ensure_session_data_integrity(self):
        """Ensures all expected fields are present in session_data."""
        default = self._default_session_data()
        for key, value in default.items():
            if key not in self.session_data:
                self.session_data[key] = value
        # Ensure all game modes are in performance tracking
        for mode in ALL_GAME_MODES:
            if mode.value not in self.session_data['game_performance']:
                self.session_data['game_performance'][mode.value] = default['game_performance'][mode.value]
        self._save_session_data() # Save any integrity fixes


    def new_day_check(self) -> bool:
        """
        Checks if it's a new day and generates a new session plan if so.

        Returns:
            True if a new session plan was generated, False otherwise.
        """
        today = datetime.now().date()
        last_played_date = self.session_data['last_played_date'].date()

        if today > last_played_date:
            print("New day detected. Generating new session plan.")
            self.session_data['last_played_date'] = datetime.now()
            self.session_data['sessions_today'] = 0
            self.session_data['structured_sessions_completed_today'] = 0
            self.session_data['last_session_number'] = 0
            self.current_session_plan = self._generate_session_plan()
            self.session_data['current_session_plan'] = {
                "state": self.current_session_plan["state"],
                "session_number": self.current_session_plan["session_number"],
                "games": [gm.value for gm in self.current_session_plan["games"]], # Store as strings
                "message": self.current_session_plan["message"],
                "game_status": self.current_session_plan["game_status"]
            }
            self._save_session_data()
            return True
        elif self.session_data['current_session_plan']:
            # Restore current_session_plan from saved data (Enum conversion)
            plan_data = self.session_data['current_session_plan']
            self.current_session_plan = {
                "state": plan_data["state"],
                "session_number": plan_data["session_number"],
                "games": [GameMode(gm_str) for gm_str in plan_data["games"]],
                "message": plan_data["message"],
                "game_status": plan_data["game_status"]
            }
        
        if not self.current_session_plan: # If it's not a new day but no plan loaded (e.g., first run today)
             self.current_session_plan = self._generate_session_plan()
             self.session_data['current_session_plan'] = {
                "state": self.current_session_plan["state"],
                "session_number": self.current_session_plan["session_number"],
                "games": [gm.value for gm in self.current_session_plan["games"]], # Store as strings
                "message": self.current_session_plan["message"],
                "game_status": self.current_session_plan["game_status"]
            }
             self._save_session_data()
        
        return False

    def _generate_session_plan(self) -> Dict:
        """Generates a structured daily session plan."""
        plan_games = []
        available_games = ALL_GAME_MODES.copy()
        
        # 1st game: Random
        plan_games.append(random.choice(available_games))
        available_games.remove(plan_games[-1])

        # 2nd game: Random from remaining
        plan_games.append(random.choice(available_games))
        available_games.remove(plan_games[-1])

        # 3rd game: Random from remaining
        plan_games.append(random.choice(available_games))
        available_games.remove(plan_games[-1])

        # 4th game: Worst performing game (or random if no performance data)
        worst_game = self._get_worst_performing_game()
        plan_games.append(worst_game)

        # 5th game: User choice (placeholder, will be "Free Play" for now)
        # Or, if only one game left, use that.
        if len(available_games) == 1:
            plan_games.append(available_games[0])
        else:
            plan_games.append(GameMode.FREE_PLAY) # Indicates user can choose in UI

        game_status = {game.value: "Pending" for game in plan_games if game != GameMode.FREE_PLAY}
        if GameMode.FREE_PLAY in plan_games:
            game_status[GameMode.FREE_PLAY.value] = "Select any game"

        return {
            "state": "structured_session",
            "session_number": self.session_data['structured_sessions_completed_today'] + 1,
            "games": plan_games,
            "message": "Complete all games for daily training!",
            "game_status": game_status
        }


    def _get_worst_performing_game(self) -> GameMode:
        """Determines the worst performing game based on average score."""
        if not self.session_data['game_performance']:
            return random.choice(ALL_GAME_MODES)

        worst_game_mode = None
        lowest_avg_score = float('inf')
        
        for mode in ALL_GAME_MODES:
            perf = self.session_data['game_performance'][mode.value]
            if perf['play_count'] > 0 and perf['avg_score'] < lowest_avg_score:
                lowest_avg_score = perf['avg_score']
                worst_game_mode = mode
        
        return worst_game_mode if worst_game_mode else random.choice(ALL_GAME_MODES)

    def get_session_plan(self) -> Dict:
        """
        Returns the current daily session plan.
        If structured sessions are completed, suggests free play.
        """
        if not self.current_session_plan:
            self.new_day_check() # Ensure plan is generated
            if not self.current_session_plan: # Fallback if new_day_check somehow failed
                return {
                    "state": "standard_menu",
                    "message": "No session plan available.",
                    "options": ["Play Finger Invaders", "Calibrate", "High Scores", "Quit"]
                }


        if self.session_data['structured_sessions_completed_today'] >= self.DAILY_SESSIONS_COUNT:
            return {
                "state": "post_structured_menu",
                "message": "You've completed your daily structured sessions!",
                "options": self.POST_STRUCTURED_MENU_OPTIONS
            }
        
        # Check if all games in current structured session are "Played"
        all_played = True
        for game_mode_enum in self.current_session_plan['games']:
            if game_mode_enum != GameMode.FREE_PLAY and self.current_session_plan['game_status'].get(game_mode_enum.value) != "Played":
                all_played = False
                break
        
        if all_played and self.current_session_plan['state'] == 'structured_session':
            # This session's games are done, but maybe not all daily sessions
            self.session_data['structured_sessions_completed_today'] += 1
            self.session_data['last_session_number'] = self.current_session_plan['session_number']
            self._save_session_data()
            return self.new_day_check() or self.get_session_plan() # Try to generate next session or show post-menu

        return self.current_session_plan

    def record_session_play(self, game_mode: GameMode, score: int, duration_seconds: float):
        """
        Records play data for a game mode.

        Args:
            game_mode: The GameMode that was played.
            score: The score achieved in the session.
            duration_seconds: How long the session lasted.
        """
        self.session_data['total_playtime_seconds'] += duration_seconds

        perf = self.session_data['game_performance'][game_mode.value]
        perf['score_history'].append(score)
        perf['last_played'] = datetime.now()
        perf['play_count'] += 1
        
        # Recalculate average score
        if perf['score_history']:
            perf['avg_score'] = sum(perf['score_history']) / len(perf['score_history'])

        # Mark game as played in current session plan
        if self.current_session_plan and self.current_session_plan['state'] == 'structured_session':
            if game_mode.value in self.current_session_plan['game_status']:
                self.current_session_plan['game_status'][game_mode.value] = "Played"
            else: # Must be a free play game during structured session
                self.current_session_plan['game_status'][game_mode.value] = "Played (Free Play)"


        self.session_data['sessions_today'] += 1
        self._save_session_data()

    def get_total_playtime(self) -> float:
        return self.session_data['total_playtime_seconds']

    def update(self, dt: float):
        """Placeholder for future timed events within the session manager."""
        pass