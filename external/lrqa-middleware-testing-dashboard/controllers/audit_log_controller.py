"""
Audit Log Controller - Read-only access to the audit trail
Currently scoped to 'sequence' entity actions (create/update/delete).
Access is restricted to super admins (see all teams) and team admins
(see only their own team's sequences) - enforced by the caller in app.py.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from models.database import Session


def _diff_queue_data(old_list: Optional[List[Dict[str, Any]]], new_list: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Produce a step-by-step diff between two sequence queue_data lists."""
    old_list = old_list or []
    new_list = new_list or []
    diffs = []
    for i in range(max(len(old_list), len(new_list))):
        old_step = old_list[i] if i < len(old_list) else None
        new_step = new_list[i] if i < len(new_list) else None

        if old_step is None and new_step is not None:
            diffs.append({
                'index': i,
                'status': 'added',
                'method': new_step.get('method'),
                'new_description': new_step.get('description'),
                'new_params': new_step.get('params')
            })
        elif new_step is None and old_step is not None:
            diffs.append({
                'index': i,
                'status': 'removed',
                'method': old_step.get('method'),
                'old_description': old_step.get('description'),
                'old_params': old_step.get('params')
            })
        else:
            changed_keys = []
            if (old_step.get('params') or {}) != (new_step.get('params') or {}):
                changed_keys.append('params')
            if old_step.get('description') != new_step.get('description'):
                changed_keys.append('description')
            if old_step.get('method') != new_step.get('method'):
                changed_keys.append('method')

            diffs.append({
                'index': i,
                'status': 'modified' if changed_keys else 'unchanged',
                'method': new_step.get('method') or old_step.get('method'),
                'old_description': old_step.get('description'),
                'new_description': new_step.get('description'),
                'old_params': old_step.get('params'),
                'new_params': new_step.get('params'),
                'changed_keys': changed_keys
            })
    return diffs


class AuditLogController:
    """Controller for reading the sequence audit trail"""

    @staticmethod
    def get_sequence_audit_log(team_name: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Fetch sequence create/update/delete audit entries, grouped by day (most recent first).

        Args:
            team_name: If provided, restrict results to entries whose old/new team_name
                       matches (used for team admins). None = all teams (super admin).
            days: How many days back to look.
        """
        session = Session()
        try:
            query = """
                SELECT a.id, a.action_type, a.entity_id, a.old_values, a.new_values,
                       a.reason, a.status, a.timestamp, a.performed_by, u.username
                FROM audit_logs a
                LEFT JOIN users u ON u.id = a.performed_by
                WHERE a.entity_type = 'sequence'
                  AND a.timestamp >= :since
            """
            from datetime import timedelta
            params = {'since': datetime.now(timezone.utc) - timedelta(days=days)}

            if team_name:
                query += """
                  AND (
                    (a.old_values->>'team_name') = :team_name
                    OR (a.new_values->>'team_name') = :team_name
                  )
                """
                params['team_name'] = team_name

            query += " ORDER BY a.timestamp DESC"

            rows = session.execute(text(query), params).fetchall()

            grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for row in rows:
                (log_id, action_type, entity_id, old_values, new_values,
                 reason, status, timestamp, performed_by, username) = row

                old_values = old_values or {}
                new_values = new_values or {}
                sequence_name = new_values.get('name') or old_values.get('name') or entity_id
                team = new_values.get('team_name') or old_values.get('team_name')

                entry = {
                    'id': log_id,
                    'action_type': action_type,
                    'sequence_id': entity_id,
                    'sequence_name': sequence_name,
                    'team_name': team,
                    'performed_by': username or 'system',
                    'status': status,
                    'reason': reason,
                    'timestamp': timestamp.isoformat() if timestamp else None
                }

                if action_type == 'create':
                    entry['queue_data'] = new_values.get('queue_data', [])
                    entry['methods'] = new_values.get('methods') or [s.get('method') for s in entry['queue_data'] if s.get('method')]
                elif action_type == 'delete':
                    entry['queue_data'] = old_values.get('queue_data', [])
                    entry['methods'] = old_values.get('methods') or [s.get('method') for s in entry['queue_data'] if s.get('method')]
                elif action_type == 'update':
                    entry['name_changed'] = old_values.get('name') != new_values.get('name')
                    entry['old_name'] = old_values.get('name')
                    entry['new_name'] = new_values.get('name')
                    entry['description_changed'] = old_values.get('description') != new_values.get('description')
                    entry['old_description'] = old_values.get('description')
                    entry['new_description'] = new_values.get('description')
                    entry['step_diff'] = _diff_queue_data(
                        old_values.get('queue_data'), new_values.get('queue_data')
                    )

                day_key = timestamp.astimezone(timezone.utc).strftime('%Y-%m-%d') if timestamp else 'unknown'
                grouped[day_key].append(entry)

            days_list = [
                {'date': day, 'entries': entries}
                for day, entries in sorted(grouped.items(), reverse=True)
            ]

            return {'success': True, 'days': days_list, 'total': len(rows)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            session.close()
