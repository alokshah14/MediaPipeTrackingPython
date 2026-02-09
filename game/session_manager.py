import json
import os
import random
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from game.constants import GameMode, ALL_GAME_MODES, SESSION_SEGMENT_DURATION

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
    def __init__(self):
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
        
        # Randomize the order of the three main games for the first 3 segments
        main_games = [GameMode.FINGER_INVADERS, GameMode.EGG_CATCHER, GameMode.PING_PONG]
        random.shuffle(main_games)
        self.state.daily_game_order = main_games
        
        # Initialize the game progression track
        self.state.game_progression_track = [main_games[0], main_games[1], main_games[2], GameMode.FREE_PLAY, GameMode.FREE_PLAY] # Placeholder for segments 4 & 5
        self.state.current_segment = 1 # Start with the first segment
        self.state.is_locked_for_day = False
        self.state.segment_playtime_ms = 0 # Reset playtime for the new segment
        self.state.segment_scores = {} # Reset scores

    def get_current_playable_games(self) -> List[GameMode]:
        if self.state.is_locked_for_day:
            return []

        if self.state.current_segment == 0: # Before any segment started (should be handled by _check_for_new_day)
            self._reset_daily_session(datetime.now().date())
            self._save_daily_state()
        
        if self.state.current_segment <= 3:
            # First 3 segments: only the current game in the randomized order is available
            current_game = self.state.daily_game_order[self.state.current_segment - 1]
            return [current_game]
        elif self.state.current_segment == 4:
            # 4th segment: lowest scoring game from the first 3
            if self.state.lowest_score_game:
                return [self.state.lowest_score_game]
            else:
                # Fallback if somehow lowest_score_game wasn't set (shouldn't happen)
                return [] 
        elif self.state.current_segment == 5:
            # 5th segment: all games are available (free play)
            return ALL_GAME_MODES
        
        return [] # Should not reach here if logic is correct

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
                message = "Determining lowest scoring game..." # Should not happen if logic is correct
        elif self.state.current_segment == 5:
            segment_game = None # User can choose any game
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

        # Ensure the game being updated is the one currently expected, or a free play game in segment 5
        if not (self.state.current_segment == 5 and game_mode_played in ALL_GAME_MODES) and \
           not (self.state.current_segment <= 3 and game_mode_played == self.state.daily_game_order[self.state.current_segment - 1]) and \
           not (self.state.current_segment == 4 and game_mode_played == self.state.lowest_score_game):
            # This case means a game was played that wasn't the "current" game for the segment.
            # This could happen if the user somehow forces a game or if there's a bug in UI enabling.
            # For now, we'll just log and ignore the playtime towards segment progression.
            print(f"Warning: Playtime for {game_mode_played.name} updated, but it's not the expected game for segment {self.state.current_segment}.")
            return
            
        self.state.segment_playtime_ms += elapsed_ms

        if self.state.segment_playtime_ms >= SESSION_SEGMENT_DURATION:
            self.state.segment_playtime_ms = SESSION_SEGMENT_DURATION # Cap at max duration

            # Record score for this segment (relevant for first 3 and 4th)
            if self.state.current_segment <= 4:
                self.state.segment_scores[game_mode_played.value] = current_score

            self.state.current_segment += 1
            self.state.segment_playtime_ms = 0 # Reset for next segment

            if self.state.current_segment == 4:
                # After 3rd segment, determine lowest scoring game
                if len(self.state.segment_scores) == 3:
                    self._determine_lowest_score_game()
                else:
                    # Fallback if not all 3 scores were recorded (shouldn't happen with forced playtime)
                    print("Warning: Not all 3 segment scores recorded for lowest score calculation.")
                    self.state.lowest_score_game = random.choice(ALL_GAME_MODES) # Default to random
                self.state.game_progression_track[3] = self.state.lowest_score_game # Update track

            elif self.state.current_segment > 5:
                # All 5 segments completed
                self.state.is_locked_for_day = True

        self._save_daily_state()

    def _determine_lowest_score_game(self):
        if not self.state.segment_scores:
            self.state.lowest_score_game = random.choice(ALL_GAME_MODES)
            return

        lowest_score = float('inf')
        lowest_game: Optional[GameMode] = None

        # Check only the games from the daily_game_order for scores
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
            return None # Means user can choose, handled by get_current_playable_games
        return None
