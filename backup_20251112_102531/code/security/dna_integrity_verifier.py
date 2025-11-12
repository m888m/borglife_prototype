"""
DNA Integrity Verification Module for BorgLife Security
Provides continuous monitoring and tampering detection for borg DNA integrity.
"""

import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from jam_mock.demo_audit_logger import DemoAuditLogger
from .dna_anchor import DNAAanchor


class DNAIntegrityVerifier:
    """
    Verifies DNA integrity by comparing local hashes with on-chain anchored hashes.

    Provides tampering detection and continuous integrity monitoring to prevent
    DNA manipulation attacks and ensure evolutionary integrity.
    """

    def __init__(self, dna_anchor: Optional[DNAAanchor] = None, audit_logger: Optional[DemoAuditLogger] = None):
        """
        Initialize DNA Integrity Verifier.

        Args:
            dna_anchor: DNA anchoring module for verification
            audit_logger: Audit logger for security events
        """
        self.dna_anchor = dna_anchor or DNAAanchor()
        self.audit_logger = audit_logger or DemoAuditLogger()

    def verify_dna_integrity(self, borg_id: str, local_dna_hash: str) -> Dict[str, Any]:
        """
        Verify DNA integrity by comparing local hash with on-chain anchor.

        Args:
            borg_id: Borg identifier
            local_dna_hash: Current local DNA hash

        Returns:
            Verification result with integrity status and details
        """
        result = {
            'borg_id': borg_id,
            'integrity_verified': False,
            'tampering_detected': False,
            'verification_details': {},
            'recommendations': [],
            'verified_at': datetime.utcnow().isoformat()
        }

        try:
            # Verify hash exists on-chain
            is_anchored = self.dna_anchor.verify_anchoring(local_dna_hash)

            if not is_anchored:
                result['tampering_detected'] = True
                result['verification_details']['anchoring_status'] = 'not_found'
                result['recommendations'].append('DNA hash not found on-chain - possible tampering or anchoring failure')
            else:
                result['integrity_verified'] = True
                result['verification_details']['anchoring_status'] = 'confirmed'

            # Log verification result
            severity = 'critical' if result['tampering_detected'] else 'info'
            self.audit_logger.log_security_event(
                'dna_integrity_check',
                'system',
                {
                    'borg_id': borg_id,
                    'integrity_verified': result['integrity_verified'],
                    'tampering_detected': result['tampering_detected'],
                    'local_dna_hash': local_dna_hash[:16] + '...',
                    'anchoring_verified': is_anchored
                },
                severity
            )

        except Exception as e:
            result['verification_details']['error'] = str(e)
            result['recommendations'].append(f'Integrity verification failed: {str(e)}')

            self.audit_logger.log_security_event(
                'dna_integrity_check_failed',
                'system',
                {
                    'borg_id': borg_id,
                    'error': str(e),
                    'local_dna_hash': local_dna_hash[:16] + '...'
                },
                'high'
            )

        return result

    def detect_dna_tampering(self, borg_id: str, original_dna: Dict[str, Any],
                           modified_dna: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect tampering by comparing original and modified DNA structures.

        Args:
            borg_id: Borg identifier
            original_dna: Original DNA structure
            modified_dna: Modified DNA structure

        Returns:
            Tampering analysis with detected changes
        """
        result = {
            'borg_id': borg_id,
            'tampering_detected': False,
            'changes_detected': [],
            'severity': 'low',
            'analysis': {},
            'analyzed_at': datetime.utcnow().isoformat()
        }

        try:
            # Compare DNA structures
            changes = self._compare_dna_structures(original_dna, modified_dna)

            if changes:
                result['tampering_detected'] = True
                result['changes_detected'] = changes

                # Assess severity
                if len(changes) > 5:
                    result['severity'] = 'high'
                elif len(changes) > 2:
                    result['severity'] = 'medium'
                else:
                    result['severity'] = 'low'

                result['analysis'] = {
                    'total_changes': len(changes),
                    'change_types': list(set(change['type'] for change in changes)),
                    'severity_assessment': result['severity']
                }

            # Log tampering detection
            if result['tampering_detected']:
                self.audit_logger.log_security_event(
                    'dna_tampering_detected',
                    'system',
                    {
                        'borg_id': borg_id,
                        'changes_count': len(changes),
                        'severity': result['severity'],
                        'change_types': result['analysis']['change_types']
                    },
                    result['severity']
                )

        except Exception as e:
            result['analysis']['error'] = str(e)
            self.audit_logger.log_security_event(
                'dna_tampering_analysis_failed',
                'system',
                {'borg_id': borg_id, 'error': str(e)},
                'medium'
            )

        return result

    def _compare_dna_structures(self, original: Dict[str, Any], modified: Dict[str, Any]) -> list:
        """
        Compare DNA structures and identify changes.

        Args:
            original: Original DNA structure
            modified: Modified DNA structure

        Returns:
            List of detected changes
        """
        changes = []

        # Compare top-level keys
        original_keys = set(original.keys())
        modified_keys = set(modified.keys())

        # Added keys
        for key in modified_keys - original_keys:
            changes.append({
                'type': 'addition',
                'field': key,
                'new_value': str(modified[key])[:100]
            })

        # Removed keys
        for key in original_keys - modified_keys:
            changes.append({
                'type': 'removal',
                'field': key,
                'old_value': str(original[key])[:100]
            })

        # Modified values
        for key in original_keys & modified_keys:
            if original[key] != modified[key]:
                changes.append({
                    'type': 'modification',
                    'field': key,
                    'old_value': str(original[key])[:100],
                    'new_value': str(modified[key])[:100]
                })

        return changes

    def get_integrity_report(self, borg_ids: list) -> Dict[str, Any]:
        """
        Generate comprehensive integrity report for multiple borgs.

        Args:
            borg_ids: List of borg IDs to check

        Returns:
            Integrity report with summary statistics
        """
        report = {
            'total_borgs': len(borg_ids),
            'integrity_checks': [],
            'summary': {
                'verified': 0,
                'tampered': 0,
                'errors': 0
            },
            'critical_findings': [],
            'generated_at': datetime.utcnow().isoformat()
        }

        for borg_id in borg_ids:
            # In a real implementation, we'd get the current DNA hash from database
            # For demo, we'll simulate integrity checks
            check_result = {
                'borg_id': borg_id,
                'status': 'verified',  # Assume verified for demo
                'last_check': datetime.utcnow().isoformat()
            }

            report['integrity_checks'].append(check_result)

            if check_result['status'] == 'verified':
                report['summary']['verified'] += 1
            elif check_result['status'] == 'tampered':
                report['summary']['tampered'] += 1
                report['critical_findings'].append(f"Borg {borg_id}: DNA tampering detected")
            else:
                report['summary']['errors'] += 1

        return report