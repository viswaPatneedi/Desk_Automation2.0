"""
Access Control Model - Manages team access to methods and sequences
Stores permissions for which teams can access specific methods and sequences
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Set
from config.config_paths import DATA_DIR

class AccessControl:
    """Model for managing team access to resources (methods/sequences)"""
    
    ACCESS_FILE = os.path.join(DATA_DIR, 'access_control.json')
    
    @staticmethod
    def _ensure_file():
        """Ensure access control file exists"""
        if not os.path.exists(AccessControl.ACCESS_FILE):
            AccessControl._save_access({
                'method_access': {},  # {method_name: [team_names]}
                'sequence_access': {}  # {sequence_id: [team_names]}
            })
    
    @staticmethod
    def _load_access() -> dict:
        """Load access control data"""
        AccessControl._ensure_file()
        try:
            with open(AccessControl.ACCESS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                'method_access': {},
                'sequence_access': {}
            }
    
    @staticmethod
    def _save_access(data: dict):
        """Save access control data"""
        os.makedirs(os.path.dirname(AccessControl.ACCESS_FILE), exist_ok=True)
        with open(AccessControl.ACCESS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def grant_team_method_access(team_name: str, method_name: str):
        """Grant a team access to a method"""
        data = AccessControl._load_access()
        if method_name not in data['method_access']:
            data['method_access'][method_name] = []
        
        if team_name not in data['method_access'][method_name]:
            data['method_access'][method_name].append(team_name)
            AccessControl._save_access(data)
    
    @staticmethod
    def revoke_team_method_access(team_name: str, method_name: str):
        """Revoke a team's access to a method"""
        data = AccessControl._load_access()
        if method_name in data['method_access']:
            if team_name in data['method_access'][method_name]:
                data['method_access'][method_name].remove(team_name)
                AccessControl._save_access(data)
    
    @staticmethod
    def get_method_access(method_name: str) -> List[str]:
        """Get list of teams with access to a method"""
        data = AccessControl._load_access()
        return data['method_access'].get(method_name, [])
    
    @staticmethod
    def grant_team_sequence_access(team_name: str, sequence_id: str):
        """Grant a team access to a sequence"""
        data = AccessControl._load_access()
        if sequence_id not in data['sequence_access']:
            data['sequence_access'][sequence_id] = []
        
        if team_name not in data['sequence_access'][sequence_id]:
            data['sequence_access'][sequence_id].append(team_name)
            AccessControl._save_access(data)
    
    @staticmethod
    def revoke_team_sequence_access(team_name: str, sequence_id: str):
        """Revoke a team's access to a sequence"""
        data = AccessControl._load_access()
        if sequence_id in data['sequence_access']:
            if team_name in data['sequence_access'][sequence_id]:
                data['sequence_access'][sequence_id].remove(team_name)
                AccessControl._save_access(data)
    
    @staticmethod
    def get_sequence_access(sequence_id: str) -> List[str]:
        """Get list of teams with access to a sequence"""
        data = AccessControl._load_access()
        return data['sequence_access'].get(sequence_id, [])
    
    @staticmethod
    def get_team_methods(team_name: str) -> List[str]:
        """Get list of methods accessible by a team"""
        data = AccessControl._load_access()
        methods = []
        for method_name, teams in data['method_access'].items():
            if team_name in teams:
                methods.append(method_name)
        return methods
    
    @staticmethod
    def get_team_sequences(team_name: str) -> List[str]:
        """Get list of sequences accessible by a team"""
        data = AccessControl._load_access()
        sequences = []
        for sequence_id, teams in data['sequence_access'].items():
            if team_name in teams:
                sequences.append(sequence_id)
        return sequences
    
    @staticmethod
    def get_all_method_access() -> dict:
        """Get access info for all methods"""
        data = AccessControl._load_access()
        return data['method_access']
    
    @staticmethod
    def get_all_sequence_access() -> dict:
        """Get access info for all sequences"""
        data = AccessControl._load_access()
        return data['sequence_access']
    
    @staticmethod
    def set_method_team_access(method_name: str, team_names: List[str]):
        """Set complete list of teams with access to a method"""
        data = AccessControl._load_access()
        data['method_access'][method_name] = team_names
        AccessControl._save_access(data)
    
    @staticmethod
    def set_sequence_team_access(sequence_id: str, team_names: List[str]):
        """Set complete list of teams with access to a sequence"""
        data = AccessControl._load_access()
        data['sequence_access'][sequence_id] = team_names
        AccessControl._save_access(data)
