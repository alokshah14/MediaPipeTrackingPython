import json
import os
import random
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from game.constants import GameMode, ALL_GAME_MODES, SESSION_SEGMENT_DURATION
from .player_manager import PlayerManager

DAILY_SESSION_FILE = "data/daily_session_state.json"

@dataclass
class DailySessionState:
    last_played_date: date = field(default_factory=lambda: date.min) # Sentinel "empty" date
    daily_game_order: List[GameMode] = field(default_factory=list)
    current_segment: int = 0 # 0 for initial state, 1-5 for actual segments
    segment_playtime_ms: int = 0
    segment_scores: Dict[str, int] = field(default_factory=dict) # GameMode.value -> score for that segment
    lowest_score_game: Optional[GameMode] = None
    is_locked_for_day: bool = False
    
    # Store the daily progression of games explicitly
    game_progression_track: List[GameMode] = field(default_factory=list)

    def to_json(self) -> Dict:
        return {
            "last_played_date": self.last_played_date.isoformat(),
            "daily_game_order": [gm.value for gm in self.daily_game_order],
            "current_segment": self.current_segment,
            "segment_playtime_ms": self.segment_playtime_ms,
            "segment_scores": self.segment_scores,
            "lowest_score_game": self.lowest_score_game.value if self.lowest_score_game else None,
            "is_locked_for_day": self.is_locked_for_day,
            "game_progression_track": [gm.value for gm in self.game_progression_track]
        }

    @classmethod
    def from_json(cls, data: Dict) -> 'DailySessionState':
        return cls(
            last_played_date=date.fromisoformat(data["last_played_date"]),
            daily_game_order=[GameMode(gm) for gm in data["daily_game_order"]],
            current_segment=data["current_segment"],
            segment_playtime_ms=data["segment_playtime_ms"],
            segment_scores=data["segment_scores"],
            lowest_score_game=GameMode(data["lowest_score_game"]) if data["lowest_score_game"] else None,
            is_locked_for_day=data["is_locked_for_day"],
            game_progression_track=[GameMode(gm) for gm in data.get("game_progression_track", [])]
        )

class DailySessionManager:
    def __init__(self, player_manager: PlayerManager):
        self.player_manager = player_manager
        self.state: DailySessionState = self._load_daily_state()
        self._check_for_new_day()

    def _load_daily_state(self) -> DailySessionState:
        if os.path.exists(DAILY_SESSION_FILE):
            try:
                with open(DAILY_SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    return DailySessionState.from_json(data)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading daily session state: {e}. Starting fresh.")
        return DailySessionState() # Return default empty state

    def _save_daily_state(self):
        try:
            os.makedirs(os.path.dirname(DAILY_SESSION_FILE), exist_ok=True)
            with open(DAILY_SESSION_FILE, 'w') as f:
                json.dump(self.state.to_json(), f, indent=2)
        except IOError as e:
            print(f"Error saving daily session state: {e}")

    def _check_for_new_day(self):
        today = datetime.now().date()
        if self.state.last_played_date != today:
            self._reset_daily_session(today)
        self._save_daily_state()

    def _reset_daily_session(self, today: date):
        print(f"New day detected ({today}). Resetting daily session.")
        self.state = DailySessionState(last_played_date=today)
        
        main_games = [GameMode.FINGER_INVADERS, GameMode.EGG_CATCHER, GameMode.PING_PONG]
        
        # Check if we should use fixed order (Home Study Week 1)
        is_week_one = self.player_manager.is_home_study and self.player_manager.get_days_since_start() < 7
        
        if is_week_one:
            print("Enforcing Week 1 Fixed Order: Invaders -> Egg -> Pong")
            # Fixed order as requested
            self.state.daily_game_order = [
                GameMode.FINGER_INVADERS,
                GameMode.EGG_CATCHER,
                GameMode.PING_PONG
            ]
        else:
            # Randomize for Lab or Week 2+
            random.shuffle(main_games)
            self.state.daily_game_order = main_games
        
        # Initialize the game progression track
        self.state.game_progression_track = [
            self.state.daily_game_order[0], 
            self.state.daily_game_order[1], 
            self.state.daily_game_order[2], 
            GameMode.FREE_PLAY, 
            GameMode.FREE_PLAY
        ]
        self.state.current_segment = 1 
        self.state.is_locked_for_day = False
        self.state.segment_playtime_ms = 0
        self.state.segment_scores = {}

    def get_current_playable_games(self) -> List[GameMode]:
        if self.state.is_locked_for_day:
            return []

        if self.state.current_segment == 0: 
            self._reset_daily_session(datetime.now().date())
            self._save_daily_state()
        
        if self.state.current_segment <= 3:
            current_game = self.state.daily_game_order[self.state.current_segment - 1]
            return [current_game]
        elif self.state.current_segment == 4:
            if self.state.lowest_score_game:
                return [self.state.lowest_score_game]
            else:
                return [] 
        elif self.state.current_segment == 5:
            return ALL_GAME_MODES
        
        return []

    def get_current_segment_info(self) -> Dict:
        if self.state.is_locked_for_day:
            return {
                "segment_number": "N/A",
                "total_segments": 5,
                "current_game": "Locked",
                "time_remaining_ms": 0,
                "message": "All sessions completed for today!"
            }

        segment_game: Optional[GameMode] = None
        message: str = ""

        if self.state.current_segment <= 3:
            segment_game = self.state.daily_game_order[self.state.current_segment - 1]
            message = f"Play {segment_game.name.replace('_', ' ').title()} for 5 minutes."
        elif self.state.current_segment == 4:
            segment_game = self.state.lowest_score_game
            if segment_game:
                message = f"Play your lowest-scoring game: {segment_game.name.replace('_', ' ').title()} for 5 minutes."
            else:
                message = "Determining lowest scoring game..." 
        elif self.state.current_segment == 5:
            segment_game = None 
            message = "Final session: Play any game for 5 minutes!"
        
        time_remaining_ms = max(0, SESSION_SEGMENT_DURATION - self.state.segment_playtime_ms)
        
        return {
            "segment_number": self.state.current_segment,
            "total_segments": 5,
            "current_game": segment_game,
            "time_remaining_ms": time_remaining_ms,
            "message": message
        }

    def update_segment_playtime(self, game_mode_played: GameMode, elapsed_ms: int, current_score: int):
        if self.state.is_locked_for_day:
            return

        if not (self.state.current_segment == 5 and game_mode_played in ALL_GAME_MODES) and \
           not (self.state.current_segment <= 3 and game_mode_played == self.state.daily_game_order[self.state.current_segment - 1]) and \
           not (self.state.current_segment == 4 and game_mode_played == self.state.lowest_score_game):
            print(f"Warning: Playtime for {game_mode_played.name} updated, but it's not the expected game for segment {self.state.current_segment}.")
            return
            
        self.state.segment_playtime_ms += elapsed_ms

        if self.state.segment_playtime_ms >= SESSION_SEGMENT_DURATION:
            self.state.segment_playtime_ms = SESSION_SEGMENT_DURATION 

            if self.state.current_segment <= 4:
                self.state.segment_scores[game_mode_played.value] = current_score

            self.state.current_segment += 1
            self.state.segment_playtime_ms = 0 

            if self.state.current_segment == 4:
                if len(self.state.segment_scores) >= 3:
                    self._determine_lowest_score_game()
                else:
                    print("Warning: Not all 3 segment scores recorded for lowest score calculation.")
                    self.state.lowest_score_game = random.choice(ALL_GAME_MODES) 
                self.state.game_progression_track[3] = self.state.lowest_score_game 

            elif self.state.current_segment > 5:
                self.state.is_locked_for_day = True

        self._save_daily_state()

    def _determine_lowest_score_game(self):
        if not self.state.segment_scores:
            self.state.lowest_score_game = random.choice(ALL_GAME_MODES)
            return

        lowest_score = float('inf')
        lowest_game: Optional[GameMode] = None

        for game_mode in self.state.daily_game_order:
            score = self.state.segment_scores.get(game_mode.value)
            if score is not None and score < lowest_score:
                lowest_score = score
                lowest_game = game_mode
        
        self.state.lowest_score_game = lowest_game if lowest_game else random.choice(ALL_GAME_MODES)

    def is_day_locked(self) -> bool:
        return self.state.is_locked_for_day

    def get_current_game_for_segment(self) -> Optional[GameMode]:
        if self.state.is_locked_for_day or self.state.current_segment == 0:
            return None
        if self.state.current_segment <= 3:
            return self.state.daily_game_order[self.state.current_segment - 1]
        elif self.state.current_segment == 4:
            return self.state.lowest_score_game
        elif self.state.current_segment == 5:
            return None 
        return None
