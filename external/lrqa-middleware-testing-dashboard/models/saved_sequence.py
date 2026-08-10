"""
Saved Sequence Model - Manages saved method sequences
Stores user-defined method sequences with custom names and input parameters
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from config.config_paths import SAVED_SEQUENCES_FILE
from models.database import Session, SavedSequence as DBSavedSequence

class SavedSequence:
    """Model for saved method sequences"""
    _last_save_storage = 'unknown'
    
    def __init__(self, name: str, queue_data: List[Dict[str, any]] = None, methods: List[str] = None,
                 user_inputs: Dict[str, any] = None, sequence_id: str = None, created_at: str = None,
                 created_by: str = None, team_name: str = None, description: str = None,
                 method_rationale: Any = None, execution_count: int = 0,
                 total_duration_seconds: float = None, average_duration_seconds: float = None,
                 location: str = None, is_active: bool = True, updated_at: str = None,
                 shared_with_teams: Dict[str, str] = None):
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
            shared_with_teams: Dict of {team_name: access_level} for teams with access
        """
        self.sequence_id = sequence_id or self._generate_id()
        self.name = name
        self.queue_data = queue_data or []
        self.methods = methods or []  # Keep for backwards compatibility
        self.user_inputs = user_inputs or {}  # Keep for backwards compatibility
        self.created_at = created_at or datetime.now().isoformat()
        self.created_by = created_by  # Track creator for permissions
        self.team_name = team_name or ''  # Team for filtering
        self.description = description or ''
        self.method_rationale = method_rationale if method_rationale is not None else []
        self.execution_count = execution_count or 0
        self.total_duration_seconds = total_duration_seconds
        self.average_duration_seconds = average_duration_seconds
        self.location = location or ''
        self.is_active = is_active
        self.updated_at = updated_at
        self.shared_with_teams = shared_with_teams or {}  # {team_name: access_level}
    
    def _generate_id(self) -> str:
        """Generate unique sequence ID"""
        from datetime import datetime
        return f"seq_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'sequence_id': self.sequence_id,
            'name': self.name,
            'description': self.description,
            'queue_data': self.queue_data,
            'methods': self.methods,  # Keep for backwards compatibility
            'user_inputs': self.user_inputs,  # Keep for backwards compatibility
            'created_at': self.created_at,
            'created_by': self.created_by,
            'team_name': self.team_name,
            'method_rationale': self.method_rationale,
            'execution_count': self.execution_count,
            'total_duration_seconds': self.total_duration_seconds,
            'average_duration_seconds': self.average_duration_seconds,
            'location': self.location,
            'is_active': self.is_active,
            'updated_at': self.updated_at,
            'shared_with_teams': self.shared_with_teams
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
            team_name=data.get('team_name'),
            description=data.get('description'),
            method_rationale=data.get('method_rationale', []),
            execution_count=data.get('execution_count', 0),
            total_duration_seconds=data.get('total_duration_seconds'),
            average_duration_seconds=data.get('average_duration_seconds'),
            location=data.get('location'),
            is_active=data.get('is_active', True),
            updated_at=data.get('updated_at'),
            shared_with_teams=data.get('shared_with_teams', {})
        )

    @staticmethod
    def _extract_methods(queue_data: List[Dict[str, any]]) -> List[str]:
        methods = []
        for item in queue_data or []:
            if isinstance(item, dict):
                method_name = item.get('method_id') or item.get('method') or item.get('name')
                if method_name:
                    methods.append(method_name)
            elif item:
                methods.append(str(item))
        return methods

    @classmethod
    def _from_db_row(cls, row: DBSavedSequence) -> 'SavedSequence':
        queue_data = row.methods or []
        return cls(
            name=row.name,
            queue_data=queue_data,
            methods=cls._extract_methods(queue_data),
            user_inputs={},
            sequence_id=row.seq_id,
            created_at=row.created_at.isoformat() if row.created_at else None,
            created_by=str(row.created_by) if row.created_by is not None else None,
            team_name=row.team_name,
            description=row.description,
            method_rationale=row.method_rationale or [],
            execution_count=row.execution_count or 0,
            total_duration_seconds=row.total_duration_seconds,
            average_duration_seconds=row.average_duration_seconds,
            location=row.location,
            is_active=row.is_active,
            updated_at=row.updated_at.isoformat() if row.updated_at else None
        )

    @classmethod
    def _load_from_db(cls) -> List['SavedSequence']:
        session = Session()
        try:
            rows = (
                session.query(DBSavedSequence)
                .filter_by(is_active=True)
                .order_by(DBSavedSequence.updated_at.desc(), DBSavedSequence.created_at.desc())
                .all()
            )
            return [cls._from_db_row(row) for row in rows]
        finally:
            session.close()

    @classmethod
    def _write_json_backup(cls, session) -> bool:
        try:
            rows = (
                session.query(DBSavedSequence)
                .order_by(DBSavedSequence.updated_at.desc(), DBSavedSequence.created_at.desc())
                .all()
            )
            sequences_dict = [cls._from_db_row(row).to_dict() for row in rows]
            os.makedirs(os.path.dirname(SAVED_SEQUENCES_FILE) or '.', exist_ok=True)
            with open(SAVED_SEQUENCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(sequences_dict, f, indent=2)
            return True
        except Exception as exc:
            print(f"[SAVE] WARNING: JSON backup sync failed: {exc}")
            return False

    @classmethod
    def _write_json_from_sequences(cls, sequences: List['SavedSequence']) -> bool:
        """Write provided sequence objects directly to JSON fallback storage."""
        try:
            payload = [seq.to_dict() for seq in (sequences or [])]
            os.makedirs(os.path.dirname(SAVED_SEQUENCES_FILE) or '.', exist_ok=True)
            with open(SAVED_SEQUENCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception as exc:
            print(f"[SAVE] ERROR: JSON direct write failed: {exc}")
            return False

    @classmethod
    def get_last_save_storage(cls) -> str:
        return str(getattr(cls, '_last_save_storage', 'unknown') or 'unknown')
    
    @classmethod
    def load_all(cls) -> List['SavedSequence']:
        """Load all saved sequences from the database, with JSON fallback"""
        try:
            db_sequences = cls._load_from_db()
            if db_sequences:
                return db_sequences
        except Exception as e:
            print(f"Error loading sequences from database: {e}")

        if not os.path.exists(SAVED_SEQUENCES_FILE):
            return []
        
        try:
            with open(SAVED_SEQUENCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [cls.from_dict(seq) for seq in data]
        except Exception as e:
            print(f"Error loading sequences: {e}")
            return []
    
    @classmethod
    def save_all(cls, sequences: List['SavedSequence']):
        """Save all sequences to the database and mirror them to JSON"""
        session = Session()
        try:
            for sequence in sequences:
                queue_data = sequence.queue_data or []
                row = session.query(DBSavedSequence).filter_by(seq_id=sequence.sequence_id).first()
                if row is None:
                    row = DBSavedSequence(
                        seq_id=sequence.sequence_id,
                        name=sequence.name,
                        description=sequence.description,
                        methods=queue_data,
                        method_rationale=sequence.method_rationale if sequence.method_rationale is not None else [],
                        execution_count=sequence.execution_count or 0,
                        total_duration_seconds=sequence.total_duration_seconds,
                        average_duration_seconds=sequence.average_duration_seconds,
                        team_name=sequence.team_name or '',
                        location=sequence.location or '',
                        is_active=sequence.is_active
                    )
                    session.add(row)
                else:
                    row.name = sequence.name
                    row.description = sequence.description
                    row.methods = queue_data
                    row.method_rationale = sequence.method_rationale if sequence.method_rationale is not None else []
                    row.execution_count = sequence.execution_count or 0
                    row.total_duration_seconds = sequence.total_duration_seconds
                    row.average_duration_seconds = sequence.average_duration_seconds
                    row.team_name = sequence.team_name or ''
                    row.location = sequence.location or ''
                    row.is_active = sequence.is_active

            session.commit()
            backup_synced = cls._write_json_backup(session)
            if not backup_synced:
                print(f"[SAVE] Database saved, but JSON backup sync failed for {len(sequences)} sequences")
                cls._last_save_storage = 'database'
            else:
                print("[SAVE] Sequences synced to database and JSON backup")
                cls._last_save_storage = 'database'
            return True
        except Exception as e:
            session.rollback()
            print(f"[SAVE] ERROR: Unexpected error saving sequences to database: {str(e)}")

            # Fallback path: persist to JSON so UI can still list saved sequences
            json_saved = cls._write_json_from_sequences(sequences)
            if json_saved:
                print("[SAVE] Fallback succeeded: sequences saved to JSON storage")
                cls._last_save_storage = 'json_fallback'
                return True

            cls._last_save_storage = 'failed'
            return False
        finally:
            session.close()
    
    @classmethod
    def add_sequence(cls, name: str, queue_data: List[Dict[str, any]] = None, methods: List[str] = None,
                    user_inputs: Dict[str, any] = None, created_by: str = None, team_name: str = None,
                    description: str = None, method_rationale: Any = None) -> 'SavedSequence':
        """Add a new saved sequence"""
        sequences = cls.load_all()
        new_sequence = cls(
            name=name,
            queue_data=queue_data,
            methods=methods,
            user_inputs=user_inputs,
            created_by=created_by,
            team_name=team_name,
            description=description,
            method_rationale=method_rationale
        )
        sequences.append(new_sequence)
        saved = cls.save_all(sequences)
        if not saved:
            raise RuntimeError('Failed to persist saved sequence')
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
                       user_inputs: Dict[str, any] = None, queue_data: List[Dict[str, any]] = None,
                       description: str = None, method_rationale: Any = None) -> bool:
        """Update an existing sequence - Enhanced with better logging and validation"""
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                # Update fields if provided
                if name is not None and name.strip():  # Check for non-empty string
                    seq.name = name
                    print(f"[UPDATE] Sequence name updated to: {name}")
                if description is not None:
                    seq.description = description
                    print("[UPDATE] Sequence description updated")
                if method_rationale is not None:
                    seq.method_rationale = method_rationale
                    print("[UPDATE] Sequence method_rationale updated")
                if methods is not None:  # Allow empty list
                    seq.methods = methods
                    print(f"[UPDATE] Sequence methods updated: {len(methods)} items")
                if user_inputs is not None:
                    seq.user_inputs = user_inputs
                    print(f"[UPDATE] Sequence user_inputs updated")
                if queue_data is not None:  # Allow empty list
                    seq.queue_data = queue_data
                    print(f"[UPDATE] Sequence queue_data updated: {len(queue_data)} items")
                    for idx, item in enumerate(queue_data):
                        print(f"  [ITEM {idx}] method={item.get('method', 'unknown')}")
                success = cls.save_all(sequences)
                print(f"[UPDATE] Sequence {sequence_id} saved: {success}")
                return success
        print(f"[UPDATE] Sequence {sequence_id} not found!")
        return False

    @classmethod
    def share_sequence_with_team(cls, sequence_id: str, team_name: str, access_level: str = 'view_clone') -> bool:
        """
        Share a sequence with another team.
        
        Args:
            sequence_id: ID of sequence to share
            team_name: Team to share with
            access_level: Permission level ('view_only', 'view_clone')
        
        Returns:
            True if successful
        """
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                if not seq.shared_with_teams:
                    seq.shared_with_teams = {}
                seq.shared_with_teams[team_name] = access_level
                print(f"[SHARE] Sequence {sequence_id} shared with {team_name} ({access_level})")
                return cls.save_all(sequences)
        print(f"[SHARE] Sequence {sequence_id} not found!")
        return False

    @classmethod
    def revoke_sequence_sharing(cls, sequence_id: str, team_name: str) -> bool:
        """
        Revoke access to sequence for a team.
        
        Args:
            sequence_id: ID of sequence
            team_name: Team to revoke access from
        
        Returns:
            True if successful
        """
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                if seq.shared_with_teams and team_name in seq.shared_with_teams:
                    del seq.shared_with_teams[team_name]
                    print(f"[REVOKE] Access to sequence {sequence_id} revoked from {team_name}")
                    return cls.save_all(sequences)
        print(f"[REVOKE] Sequence {sequence_id} not found!")
        return False

    @classmethod
    def clone_sequence(cls, sequence_id: str, new_name: str, new_team: str, cloned_by: str) -> Optional['SavedSequence']:
        """
        Clone an existing sequence to a new team.
        
        Args:
            sequence_id: ID of sequence to clone
            new_name: Name for the cloned sequence
            new_team: Team to assign cloned sequence to
            cloned_by: Username who initiated the clone
        
        Returns:
            New SavedSequence instance if successful, None otherwise
        """
        sequences = cls.load_all()
        for seq in sequences:
            if seq.sequence_id == sequence_id:
                # Create a new sequence with same data
                cloned_seq = cls(
                    name=new_name,
                    queue_data=seq.queue_data.copy() if seq.queue_data else [],
                    methods=seq.methods.copy() if seq.methods else [],
                    user_inputs=seq.user_inputs.copy() if seq.user_inputs else {},
                    created_by=cloned_by,
                    team_name=new_team,
                    description=f"Clone of '{seq.name}' (Original by {seq.created_by})",
                    method_rationale=seq.method_rationale.copy() if seq.method_rationale else [],
                    location=seq.location
                )
                sequences.append(cloned_seq)
                if cls.save_all(sequences):
                    print(f"[CLONE] Sequence {sequence_id} cloned by {cloned_by} to team {new_team}")
                    return cloned_seq
        print(f"[CLONE] Sequence {sequence_id} not found!")
        return None
