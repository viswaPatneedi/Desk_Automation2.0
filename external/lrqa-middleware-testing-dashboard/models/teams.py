"""
Teams Model - Manages team metadata
Tracks all teams created in the system, with or without members
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class Teams:
    """Model for managing team metadata"""
    
    TEAMS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Json', 'teams.json')
    
    @staticmethod
    def _ensure_file():
        """Ensure teams file exists"""
        if not os.path.exists(Teams.TEAMS_FILE):
            Teams._save_teams({})
    
    @staticmethod
    def _load_teams() -> dict:
        """Load teams metadata"""
        Teams._ensure_file()
        try:
            with open(Teams.TEAMS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def _save_teams(data: dict):
        """Save teams metadata"""
        os.makedirs(os.path.dirname(Teams.TEAMS_FILE), exist_ok=True)
        with open(Teams.TEAMS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def create_team(team_name: str, description: str = '') -> bool:
        """Create a new team metadata entry"""
        teams = Teams._load_teams()
        
        if team_name in teams:
            return False  # Team already exists
        
        teams[team_name] = {
            'team_name': team_name,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'member_count': 0
        }
        Teams._save_teams(teams)
        return True
    
    @staticmethod
    def delete_team(team_name: str) -> bool:
        """Delete a team metadata entry"""
        teams = Teams._load_teams()
        
        if team_name in teams:
            del teams[team_name]
            Teams._save_teams(teams)
            return True
        return False
    
    @staticmethod
    def get_team(team_name: str) -> Optional[dict]:
        """Get team metadata"""
        teams = Teams._load_teams()
        return teams.get(team_name)
    
    @staticmethod
    def get_all_teams() -> dict:
        """Get all teams metadata"""
        return Teams._load_teams()
    
    @staticmethod
    def update_team(team_name: str, description: str = None) -> bool:
        """Update team metadata"""
        teams = Teams._load_teams()
        
        if team_name not in teams:
            return False
        
        if description is not None:
            teams[team_name]['description'] = description
        
        Teams._save_teams(teams)
        return True
    
    @staticmethod
    def team_exists(team_name: str) -> bool:
        """Check if a team exists"""
        teams = Teams._load_teams()
        return team_name in teams
