"""
Audit Logging for BorgLife Demo
Complete audit trail for all demo operations with compliance reporting.
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path


class DemoAuditLogger:
    """Comprehensive audit logging for demo operations"""

    def __init__(self, log_path: str = "code/jam_mock/logs/demo_audit.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def log_operation(self, operation: str, user_id: str, details: Dict[str, Any],
                     status: str = 'success', error_details: str = None) -> bool:
        """Log all demo operations with full context"""
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': self.session_id,
                'operation': operation,
                'user_id': user_id,
                'status': status,
                'details': details,
                'error_details': error_details,
                'environment': {
                    'user': os.getenv('USER', 'unknown'),
                    'hostname': os.getenv('HOSTNAME', 'unknown'),
                    'python_version': os.sys.version.split()[0] if 'os' in globals() else 'unknown'
                }
            }

            # Write to JSONL file
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            # Also print for immediate visibility in development
            status_icon = '✅' if status == 'success' else '❌' if status == 'error' else '⚠️'
            print(f"{status_icon} AUDIT: {operation} by {user_id} - {status}")

            return True
        except Exception as e:
            print(f"Failed to write audit log: {e}")
            return False

    def log_keypair_access(self, action: str, keypair_name: str, user_id: str,
                          address: str = None, status: str = 'success') -> bool:
        """Log keypair access operations"""
        details = {
            'keypair_name': keypair_name,
            'action': action,
            'address': address or 'unknown'
        }
        return self.log_operation('keypair_access', user_id, details, status)

    def log_transaction_operation(self, operation: str, user_id: str,
                                tx_hash: str = None, amount: str = None,
                                status: str = 'success') -> bool:
        """Log transaction operations"""
        details = {
            'tx_hash': tx_hash,
            'amount': amount,
            'operation_type': operation
        }
        return self.log_operation('transaction', user_id, details, status)

    def log_validation_operation(self, validation_type: str, user_id: str,
                               target: str, status: str = 'success',
                               errors: List[str] = None) -> bool:
        """Log validation operations"""
        details = {
            'validation_type': validation_type,
            'target': target,
            'errors': errors or []
        }
        return self.log_operation('validation', user_id, details, status)

    def log_security_event(self, event_type: str, user_id: str,
                          details: Dict[str, Any], severity: str = 'info') -> bool:
        """Log security-related events"""
        security_details = {
            'event_type': event_type,
            'severity': severity,
            **details
        }
        status = 'error' if severity in ['high', 'critical'] else 'warning' if severity == 'medium' else 'success'
        return self.log_operation('security_event', user_id, security_details, status)

    def get_audit_trail(self, user_id: str = None, operation: str = None,
                       start_time: str = None, end_time: str = None) -> List[Dict]:
        """Retrieve audit trail with optional filtering"""
        try:
            if not self.log_path.exists():
                return []

            entries = []
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)

                        # Apply filters
                        if user_id and entry.get('user_id') != user_id:
                            continue
                        if operation and entry.get('operation') != operation:
                            continue
                        if start_time and entry.get('timestamp', '') < start_time:
                            continue
                        if end_time and entry.get('timestamp', '') > end_time:
                            continue

                        entries.append(entry)

            return entries
        except Exception as e:
            print(f"Failed to read audit trail: {e}")
            return []

    def generate_compliance_report(self, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """Generate compliance report for audit purposes"""
        entries = self.get_audit_trail(start_time=start_time, end_time=end_time)

        report = {
            'report_generated': datetime.utcnow().isoformat(),
            'time_range': {
                'start': start_time,
                'end': end_time or datetime.utcnow().isoformat()
            },
            'total_operations': len(entries),
            'operations_by_type': {},
            'operations_by_status': {},
            'operations_by_user': {},
            'security_events': [],
            'error_summary': []
        }

        for entry in entries:
            # Count by operation type
            op_type = entry.get('operation', 'unknown')
            report['operations_by_type'][op_type] = report['operations_by_type'].get(op_type, 0) + 1

            # Count by status
            status = entry.get('status', 'unknown')
            report['operations_by_status'][status] = report['operations_by_status'].get(status, 0) + 1

            # Count by user
            user = entry.get('user_id', 'unknown')
            report['operations_by_user'][user] = report['operations_by_user'].get(user, 0) + 1

            # Collect security events
            if op_type == 'security_event':
                report['security_events'].append(entry)

            # Collect errors
            if status == 'error' and entry.get('error_details'):
                report['error_summary'].append({
                    'timestamp': entry.get('timestamp'),
                    'operation': op_type,
                    'user': user,
                    'error': entry.get('error_details')
                })

        return report

    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old audit logs beyond retention period"""
        try:
            if not self.log_path.exists():
                return 0

            cutoff_date = datetime.utcnow().timestamp() - (days_to_keep * 24 * 60 * 60)
            temp_entries = []

            # Read all entries
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        entry_timestamp = datetime.fromisoformat(entry['timestamp']).timestamp()
                        if entry_timestamp > cutoff_date:
                            temp_entries.append(entry)

            # Write back only recent entries
            with open(self.log_path, 'w', encoding='utf-8') as f:
                for entry in temp_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

            removed_count = len(temp_entries) - len(temp_entries) if 'temp_entries' in locals() else 0
            print(f"Cleaned up {removed_count} old audit log entries")
            return removed_count

        except Exception as e:
            print(f"Failed to cleanup audit logs: {e}")
            return 0