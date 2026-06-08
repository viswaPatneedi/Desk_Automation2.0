"""
Saved Sequence Model - Manages saved method sequences
Stores user-defined method sequences with custom names and input parameters
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from config_paths import SAVED_SEQUENCES_FILE

class SavedSequence:
    """Model for saved method sequences"""
    
    def __init__(self, name: str, queue_data: List[Dict[str, any]] = None, methods: List[str] = None,
                 user_inputs: Dict[str, any] = None, sequence_id: str = None, created_at: str = None, created_by: str = None, team_name: str = None):
        """
        Initialize a saved sequence
        
        Args:
            name: User-friendly name for the sequence
            queue_data: List of {method: str, ir_keys: list, voice_text: str} (new format)
            methods: List of method names in order (old format - for backwards compatibility)
            user_inputs: Dictionary of user inputs (old format - for backwards compatibility)
            sequence_id: Unique identifier
            created_at: Creation timestamp
            created_by: Username/NTID of creator
            team_name: Team this sequence belongs to
        """
        self.sequence_id = sequence_id or self._generate_id()
        self.name = name
        self.queue_data = queue_data or []
        self.methods = methods or []  # Keep for backwards compatibility
        self.user_inputs = user_inputs or {}  # Keep for backwards compatibility
        self.created_at = created_at or datetime.now().isoformat()
        self.created_by = created_by  # Track creator for permissions
        self.team_name = team_name or ''  # Team for filtering
    
    def _generate_id(self) -> str:
        """Generate unique sequence ID"""
        from datetime import datetime
        return f"seq_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'sequence_id': self.sequence_id,
            'name': self.name,
            'queue_data': self.queue_data,
            'methods': self.methods,  # Keep for backwards compatibility
            'user_inputs': self.user_inputs,  # Keep for backwards compatibility
            'created_at': self.created_at,
            'created_by': self.created_by,
            'team_name': self.team_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SavedSequence':
        """Create instance from dictionary"""
        return cls(
            name=data['name'],
            queue_data=data.get('queue_data', []),
            methods=data.get('methods', []),
            user_inputs=data.get('user_inputs', {}),
            sequence_id=data.get('sequence_id'),
            created_at=data.get('created_at'),
            created_by=data.get('created_by'),
            team_name=data.get('team_name')
        )
    
    @classmethod
    def load_all(cls) -> List['SavedSequence']:
        """Load all saved sequences from file"""
        if not os.path.exists(SAVED_SEQUENCES_FILE):
            return []
        
        try:
            with open(SAVED_SEQUENCES_FILE, 'r') as f:
                data = json.load(f)
                return [cls.from_dict(seq) for seq in data]
        except Exception as e:
            print(f"Error loading sequences: {e}")
            return []
    
    @classmethod
    def save_all(cls, sequences: List['SavedSequence']):
        """Save all sequences to file"""
        try:
            with open(SAVED_SEQUENCES_FILE, 'w') as f:
                json.dump([seq.to_dict() for seq in sequences], f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving sequences: {e}")
            return False
    
    @classmethod
    def add_sequence(cls, name: str, queue_data: List[Dict[str, any]] = None, methods: List[str] = None, 
                    user_inputs: Dict[str, any] = None, created_by: str = None, team_name: str = None) -> 'SavedSequence':
        """Add a new saved sequence"""
        sequences = cls.load_all()
        new_sequence = cls(name=name, queue_data=queue_data, methods=methods, user_inputs=user_inputs, created_by=created_by, team_name=team_name)
        sequences.append(new_sequence)
        cls.save_all(sequences)
        return new_sequence
    
    @classmethod
    def delete_sequence(cls, sequence_id: str) -> bool:
        """Delete a sequence by ID"""
        sequences = cls.load_all()
        sequences = [seq for seq in sequences if seq.sequence_id != sequence_id]
        return cls.save_all(sequences)
    
    @classmethod
    def find_by_id(cls, sequence_id: str) -> Optional['SavedSequence']:
        """Find sequence by ID"""
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                return seq
        return None
    
    @classmethod
    def update_sequence(cls, sequence_id: str, name: str = None, methods: List[str] = None, 
                       user_inputs: Dict[str, any] = None, queue_data: List[Dict[str, any]] = None) -> bool:
        """Update an existing sequence"""
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                if name:
                    seq.name = name
                if methods:
                    seq.methods = methods
                if user_inputs is not None:
                    seq.user_inputs = user_inputs
                if queue_data is not None:
                    seq.queue_data = queue_data
                return cls.save_all(sequences)
        return False
