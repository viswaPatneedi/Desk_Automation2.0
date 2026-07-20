"""
Audit Logging Service - v2.0 Enterprise Implementation
Tracks all CRUD operations on critical resources with full audit trail
"""

import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from models.database import Session, AuditLog, Base
from sqlalchemy.exc import OperationalError, SQLAlchemyError


class AuditLoggingService:
    """Service for comprehensive audit logging of database transactions"""
    
    @staticmethod
    def log_action(
        action_type: str,
        entity_type: str,
        entity_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        reason: str = None,
        status: str = 'success',
        impact_assessment: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an action to the audit log table.
        
        Args:
            action_type: 'create', 'update', 'delete', 'approve', 'reject', 'deploy'
            entity_type: 'device', 'job', 'sequence', 'user', 'team', etc.
            entity_id: ID of the entity being modified
            old_values: Previous state (for updates/deletes)
            new_values: New state (for creates/updates)
            reason: Why this action was performed
            status: 'success' or 'failure'
            impact_assessment: Risk assessment for the change
        
        Returns:
            bool: True if logged successfully, False otherwise
        """
        session = Session()
        try:
            # Get current user if available (deferred import to avoid circular dependency)
            performed_by_user_id = None
            performed_by_ntid = "system"
            
            try:
                from flask_login import current_user
                if current_user and hasattr(current_user, 'user_id'):
                    performed_by_ntid = current_user.ntid or "unknown"
            except Exception as e:
                pass  # Flask context not available, use system
            
            # Create audit log entry
            audit_log = AuditLog(
                action_type=action_type,
                entity_type=entity_type,
                entity_id=str(entity_id),
                performed_by=performed_by_user_id,
                old_values=old_values or {},
                new_values=new_values or {},
                reason=reason,
                status=status,
                impact_assessment=impact_assessment or {},
                timestamp=datetime.now(timezone.utc),
                is_immutable=True
            )
            
            session.add(audit_log)
            session.commit()
            
            # Log to stderr for immediate visibility
            log_msg = f"✅ [AUDIT] {action_type.upper()}: {entity_type}#{entity_id} by {performed_by_ntid} [{status.upper()}]"
            print(log_msg, file=sys.stderr)
            
            return True
            
        except OperationalError as e:
            session.rollback()
            print(f"⚠️  [AUDIT] Database connection error: {e}", file=sys.stderr)
            # Still log to stderr as fallback
            print(f"⚠️  [AUDIT_FALLBACK] {action_type.upper()}: {entity_type}#{entity_id} [{status}]", file=sys.stderr)
            return False
        except Exception as e:
            session.rollback()
            print(f"❌ [AUDIT] Error logging action: {e}", file=sys.stderr)
            return False
        finally:
            session.close()
    
    @staticmethod
    def log_database_transaction(transaction_type: str, details: Dict[str, Any]) -> bool:
        """
        Log database transaction for audit trail.
        
        Args:
            transaction_type: 'commit', 'rollback', 'connection_error'
            details: Transaction details (table, operation, timestamp, etc.)
        
        Returns:
            bool: True if logged successfully
        """
        session = Session()
        try:
            audit_log = AuditLog(
                action_type=f'db_{transaction_type}',
                entity_type='database_transaction',
                entity_id=details.get('transaction_id', 'unknown'),
                new_values=details,
                status='success',
                timestamp=datetime.now(timezone.utc)
            )
            
            session.add(audit_log)
            session.commit()
            
            if transaction_type == 'commit':
                print(
                    f"✅ [DB_COMMIT] {details.get('operation', 'unknown')} "
                    f"on {details.get('table', 'unknown')}: "
                    f"{details.get('record_count', 1)} record(s)",
                    file=sys.stderr
                )
            
            return True
        except Exception as e:
            session.rollback()
            print(f"⚠️  [DB_TRANSACTION] Logging failed: {e}", file=sys.stderr)
            return False
        finally:
            session.close()
    
    @staticmethod
    def create_impact_assessment(
        entity_type: str,
        changes: Dict[str, Any],
        affected_resources: list = None
    ) -> Dict[str, Any]:
        """
        Create an impact assessment for a change.
        
        Args:
            entity_type: Type of entity being changed
            changes: Dictionary of changes
            affected_resources: List of affected resources
        
        Returns:
            Dict with risk level, affected count, and recommendations
        """
        risk_level = 'low'
        affected_count = len(affected_resources) if affected_resources else 0
        recommendations = []
        
        # Determine risk level based on entity type and changes
        if entity_type == 'device':
            if 'ip' in changes or 'credentials' in changes:
                risk_level = 'high'
                recommendations.append('IP/credential changes may affect running jobs')
                recommendations.append('Verify no active jobs on this device')
        elif entity_type == 'user':
            if 'is_super_admin' in changes or 'is_team_admin' in changes:
                risk_level = 'critical'
                recommendations.append('Admin role changes affect system-wide permissions')
                recommendations.append('Audit affected user access after change')
        elif entity_type == 'job':
            if 'status' in changes:
                risk_level = 'medium'
                recommendations.append('Job status change affects device availability')
        elif entity_type == 'saved_sequence':
            if 'queue_data' in changes:
                risk_level = 'medium'
                recommendations.append('Sequence changes affect future executions')
                recommendations.append(f'Estimated {affected_count} users affected')
        
        return {
            'risk_level': risk_level,
            'affected_resource_count': affected_count,
            'affected_resources': affected_resources or [],
            'recommendations': recommendations,
            'assessment_timestamp': datetime.now(timezone.utc).isoformat()
        }


class TransactionRollbackHandler:
    """Handle transaction rollback and recovery on errors"""
    
    @staticmethod
    def execute_with_rollback(operation_func, operation_name: str, entity_type: str, entity_id: str):
        """
        Execute an operation with automatic rollback on error.
        
        Args:
            operation_func: Function to execute (should accept session as parameter)
            operation_name: Name of operation for logging
            entity_type: Type of entity being modified
            entity_id: ID of entity being modified
        
        Returns:
            Tuple of (success: bool, result: Any, error_message: str)
        """
        session = Session()
        try:
            print(
                f"[TRANSACTION] Starting: {operation_name} on {entity_type}#{entity_id}",
                file=sys.stderr
            )
            
            result = operation_func(session)
            
            session.commit()
            
            print(
                f"✅ [TRANSACTION] SUCCESS: {operation_name} on {entity_type}#{entity_id}",
                file=sys.stderr
            )
            
            # Log successful transaction
            AuditLoggingService.log_database_transaction('commit', {
                'transaction_id': f"{entity_type}#{entity_id}",
                'operation': operation_name,
                'table': entity_type,
                'record_count': 1
            })
            
            return True, result, None
            
        except SQLAlchemyError as db_error:
            session.rollback()
            error_msg = f"Database error in {operation_name}: {str(db_error)}"
            print(f"❌ [TRANSACTION] ROLLBACK: {error_msg}", file=sys.stderr)
            
            # Log rollback
            AuditLoggingService.log_database_transaction('rollback', {
                'transaction_id': f"{entity_type}#{entity_id}",
                'operation': operation_name,
                'error': str(db_error)
            })
            
            return False, None, error_msg
            
        except Exception as e:
            session.rollback()
            error_msg = f"Unexpected error in {operation_name}: {str(e)}"
            print(f"❌ [TRANSACTION] ROLLBACK: {error_msg}", file=sys.stderr)
            
            return False, None, error_msg
            
        finally:
            session.close()
    
    @staticmethod
    def execute_batch_with_rollback(operations: list, batch_name: str):
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of (func, entity_type, entity_id) tuples
            batch_name: Name of batch operation for logging
        
        Returns:
            Tuple of (success: bool, results: list, error_message: str)
        """
        session = Session()
        results = []
        try:
            print(
                f"[BATCH_TRANSACTION] Starting: {batch_name} ({len(operations)} operations)",
                file=sys.stderr
            )
            
            for operation_func, entity_type, entity_id in operations:
                result = operation_func(session)
                results.append(result)
            
            session.commit()
            
            print(
                f"✅ [BATCH_TRANSACTION] SUCCESS: {batch_name} ({len(operations)} operations completed)",
                file=sys.stderr
            )
            
            # Log successful batch
            AuditLoggingService.log_database_transaction('commit', {
                'transaction_id': f"batch#{batch_name}",
                'operation': batch_name,
                'table': 'multiple',
                'record_count': len(operations)
            })
            
            return True, results, None
            
        except SQLAlchemyError as db_error:
            session.rollback()
            error_msg = f"Database error in batch {batch_name}: {str(db_error)}"
            print(f"❌ [BATCH_TRANSACTION] ROLLBACK: All {len(operations)} operations rolled back", file=sys.stderr)
            print(f"   Error: {error_msg}", file=sys.stderr)
            
            # Log rollback
            AuditLoggingService.log_database_transaction('rollback', {
                'transaction_id': f"batch#{batch_name}",
                'operation': batch_name,
                'rolled_back_count': len(operations),
                'error': str(db_error)
            })
            
            return False, results, error_msg
            
        except Exception as e:
            session.rollback()
            error_msg = f"Unexpected error in batch {batch_name}: {str(e)}"
            print(f"❌ [BATCH_TRANSACTION] ROLLBACK: {error_msg}", file=sys.stderr)
            
            return False, results, error_msg
            
        finally:
            session.close()


class DataVersioningService:
    """Implement data versioning and temporal queries for compliance"""
    
    @staticmethod
    def get_entity_history(entity_type: str, entity_id: str, limit: int = 100):
        """
        Get complete audit history for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            limit: Maximum number of records to return
        
        Returns:
            List of audit log entries for the entity
        """
        session = Session()
        try:
            history = (
                session.query(AuditLog)
                .filter_by(entity_type=entity_type, entity_id=str(entity_id))
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    'id': log.id,
                    'action_type': log.action_type,
                    'performed_by': log.performed_by,
                    'old_values': log.old_values,
                    'new_values': log.new_values,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'reason': log.reason,
                    'status': log.status
                }
                for log in history
            ]
        finally:
            session.close()
    
    @staticmethod
    def get_entity_at_timestamp(entity_type: str, entity_id: str, timestamp: datetime):
        """
        Reconstruct entity state at a specific point in time.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            timestamp: Point in time to retrieve
        
        Returns:
            Entity state at that time, or None if not found
        """
        history = DataVersioningService.get_entity_history(entity_type, entity_id, limit=1000)
        
        # Filter to changes before the timestamp
        relevant_changes = [
            log for log in history
            if datetime.fromisoformat(log['timestamp']) <= timestamp
        ]
        
        if not relevant_changes:
            return None
        
        # Reconstruct by applying changes in reverse chronological order
        state = {}
        for log in reversed(relevant_changes):
            if log['action_type'] == 'create':
                state = log['new_values']
                break
            elif log['action_type'] == 'update':
                state.update(log['new_values'])
        
        return state if state else None
