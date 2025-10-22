from typing import Dict, Any
import re
from datetime import datetime, timedelta

class MCPSecurityManager:
    """Security controls for Docker MCP organ interactions"""

    def __init__(self):
        self.rate_limits = {}  # organ_name -> {count, reset_time}
        self.audit_log = []
        self.blocked_patterns = [
            r'.*DROP\s+TABLE.*',  # SQL injection
            r'.*;\s*rm\s+-rf.*',  # Command injection
            r'.*<script>.*',      # XSS
        ]

    def validate_input(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters for security threats

        Returns:
            True if safe, raises SecurityError if malicious
        """
        # Convert params to string for pattern matching
        param_str = str(params)

        for pattern in self.blocked_patterns:
            if re.search(pattern, param_str, re.IGNORECASE):
                self.audit_log.append({
                    'timestamp': datetime.utcnow(),
                    'event': 'blocked_input',
                    'pattern': pattern,
                    'params': params
                })
                raise SecurityError(f"Malicious pattern detected: {pattern}")

        return True

    def check_rate_limit(self, organ_name: str, limit: int = 100) -> bool:
        """
        Check if organ rate limit is exceeded

        Args:
            organ_name: Name of Docker MCP organ
            limit: Max calls per hour

        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.utcnow()

        if organ_name not in self.rate_limits:
            self.rate_limits[organ_name] = {
                'count': 0,
                'reset_time': now + timedelta(hours=1)
            }

        rate_limit = self.rate_limits[organ_name]

        # Reset if time window expired
        if now >= rate_limit['reset_time']:
            rate_limit['count'] = 0
            rate_limit['reset_time'] = now + timedelta(hours=1)

        # Check limit
        if rate_limit['count'] >= limit:
            return False

        rate_limit['count'] += 1
        return True

    def audit_organ_call(
        self,
        organ_name: str,
        tool: str,
        params: Dict[str, Any],
        result: Any,
        cost: float
    ):
        """Audit log all organ calls for security review"""
        self.audit_log.append({
            'timestamp': datetime.utcnow(),
            'organ': organ_name,
            'tool': tool,
            'params': params,  # May need to redact sensitive data
            'result_size': len(str(result)),
            'cost': cost,
            'user': 'sponsor_id_here'  # Track who made the call
        })

        # Persist to Supabase for long-term audit
        # self._persist_audit_log()