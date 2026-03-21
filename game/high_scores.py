"""High score persistence for tracking best performances."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from .constants import GameMode, DATA_DIR

@dataclass
class HighScoreEntry:
    """A single high score entry."""
    score: int
    date: str
    game_mode: str
    duration_seconds: float
    accuracy: float
    clean_trial_rate: float
    avg_reaction_time_ms: float


class HighScoreManager:
    """Manages high score persistence across game sessions."""

    MAX_SCORES_PER_MODE = 10  # Keep top 10 for each game mode

    def __init__(self, filepath: str = None):
        if filepath is None:
            import os
            filepath = os.path.join(DATA_DIR, "high_scores.json")
        """
        Initialize the high score manager.

        Args:
            filepath: Path to the high scores JSON file
        """
        self.filepath = filepath
        self.scores: Dict[str, List[HighScoreEntry]] = {}
        self._load_scores()

    def _load_scores(self):
        """Load high scores from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    # Convert dicts back to HighScoreEntry objects
                    for mode, entries in data.items():
                        self.scores[mode] = [
                            HighScoreEntry(**entry) for entry in entries
                        ]
            except (json.JSONDecodeError, IOError, TypeError) as e:
                print(f"Warning: Could not load high scores: {e}")
                self.scores = {}
        else:
            self.scores = {}

    def _save_scores(self):
        """Save high scores to file."""
        try:
            # Convert HighScoreEntry objects to dicts
            data = {
                mode: [asdict(entry) for entry in entries]
                for mode, entries in self.scores.items()
            }
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving high scores: {e}")

    def add_score(
        self,
        score: int,
        game_mode: str = "classic",
        duration_seconds: float = 0,
        accuracy: float = 0,
        clean_trial_rate: float = 0,
        avg_reaction_time_ms: float = 0
    ) -> Optional[int]:
        """
        Add a new score and return its rank if it's a high score.

        Args:
            score: The score achieved
            game_mode: The game mode played
            duration_seconds: How long the session lasted
            accuracy: Percentage of correct presses
            clean_trial_rate: Percentage of clean trials
            avg_reaction_time_ms: Average reaction time

        Returns:
            Rank (1-10) if it's a new high score, None otherwise
        """
        entry = HighScoreEntry(
            score=score,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            game_mode=game_mode,
            duration_seconds=round(duration_seconds, 1),
            accuracy=round(accuracy, 1),
            clean_trial_rate=round(clean_trial_rate, 1),
            avg_reaction_time_ms=round(avg_reaction_time_ms, 1)
        )

        # Initialize mode list if needed
        if game_mode not in self.scores:
            self.scores[game_mode] = []

        mode_scores = self.scores[game_mode]

        # Find position for new score
        position = 0
        for i, existing in enumerate(mode_scores):
            if score > existing.score:
                position = i
                break
            position = i + 1

        # Check if it qualifies as a high score
        if position < self.MAX_SCORES_PER_MODE:
            mode_scores.insert(position, entry)
            # Trim to max size
            self.scores[game_mode] = mode_scores[:self.MAX_SCORES_PER_MODE]
            self._save_scores()
            return position + 1  # Return 1-indexed rank

        return None

    def get_high_scores(self, game_mode: str = "classic") -> List[HighScoreEntry]:
        """
        Get high scores for a game mode.

        Args:
            game_mode: The game mode to get scores for

        Returns:
            List of high score entries, sorted by score descending
        """
        return self.scores.get(game_mode, [])

    def get_top_score(self, game_mode: str = "classic") -> Optional[int]:
        """
        Get the top score for a game mode.

        Args:
            game_mode: The game mode

        Returns:
            The highest score, or None if no scores exist
        """
        scores = self.scores.get(game_mode, [])
        return scores[0].score if scores else None

    def is_high_score(self, score: int, game_mode: str = "classic") -> bool:
        """
        Check if a score would be a high score.

        Args:
            score: The score to check
            game_mode: The game mode

        Returns:
            True if this would be a new high score
        """
        mode_scores = self.scores.get(game_mode, [])

        if len(mode_scores) < self.MAX_SCORES_PER_MODE:
            return True

        return score > mode_scores[-1].score

    def get_all_modes(self) -> List[str]:
        """Get list of all game modes with scores."""
        return list(self.scores.keys())

    def clear_scores(self, game_mode: Optional[str] = None):
        """
        Clear high scores.

        Args:
            game_mode: Specific mode to clear, or None to clear all
        """
        if game_mode:
            if game_mode in self.scores:
                del self.scores[game_mode]
        else:
            self.scores = {}
        self._save_scores()
