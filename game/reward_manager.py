import json
import os
from typing import Dict, List, Any, Optional


class RewardManager:
    REWARDS_FILE = "data/rewards.json"
    REWARDS_CONFIG = [
        {"name": "Bronze Player", "threshold_playtime_seconds": 60 * 5, "type": "skin", "value": "bronze_skin"},
        {"name": "Silver Player", "threshold_playtime_seconds": 60 * 15, "type": "skin", "value": "silver_skin"},
        {"name": "Gold Player", "threshold_playtime_seconds": 60 * 30, "type": "skin", "value": "gold_skin"},
        {"name": "Paddle Master", "threshold_playtime_seconds": 60 * 60, "type": "paddle", "value": "advanced_paddle"},
        # Add more rewards here
    ]

    def __init__(self):
        self.unlocked_rewards = self._load_rewards()

    def _load_rewards(self) -> List[str]:
        """Loads unlocked rewards from file."""
        if os.path.exists(self.REWARDS_FILE):
            try:
                with open(self.REWARDS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading rewards data: {e}. Starting fresh.")
        return []

    def _save_rewards(self):
        """Saves current unlocked rewards to file."""
        try:
            # Ensure data/ directory exists
            os.makedirs(os.path.dirname(self.REWARDS_FILE), exist_ok=True)
            with open(self.REWARDS_FILE, 'w') as f:
                json.dump(self.unlocked_rewards, f, indent=2)
        except IOError as e:
            print(f"Error saving rewards data: {e}")

    def add_playtime(self, total_playtime_seconds: float) -> List[str]:
        """
        Checks for and unlocks new rewards based on total playtime.

        Args:
            total_playtime_seconds: The cumulative playtime across all sessions.

        Returns:
            A list of names of newly unlocked rewards.
        """
        newly_unlocked = []
        for reward in self.REWARDS_CONFIG:
            if (reward["name"] not in self.unlocked_rewards and 
               total_playtime_seconds >= reward["threshold_playtime_seconds"]):
                self.unlocked_rewards.append(reward["name"])
                newly_unlocked.append(reward["name"])
        
        if newly_unlocked:
            self._save_rewards()
        
        return newly_unlocked

    def get_unlocked_rewards(self) -> List[str]:
        """Returns a list of all currently unlocked reward names."""
        return self.unlocked_rewards
    
    def is_reward_unlocked(self, reward_name: str) -> bool:
        """Checks if a specific reward is unlocked."""
        return reward_name in self.unlocked_rewards
    
    def get_reward_details(self, reward_name: str) -> Optional[Dict[str, Any]]:
        """Returns details for a specific reward."""
        for reward in self.REWARDS_CONFIG:
            if reward["name"] == reward_name:
                return reward
        return None