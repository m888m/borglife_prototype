from typing import Dict, List, Optional, Tuple
from packaging import version
import semver

class DockerMCPCompatibilityMatrix:
    """Manage Docker MCP organ version compatibility"""

    # Compatibility matrix: organ -> version -> borglife requirements
    COMPATIBILITY_MATRIX = {
        'gmail': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.2.0', 'deprecated': False},
            '1.1.0': {'min_borglife': '1.0.0', 'max_borglife': '1.3.0', 'deprecated': False},
            '1.2.0': {'min_borglife': '1.1.0', 'max_borglife': '1.4.0', 'deprecated': False},
            '1.3.0': {'min_borglife': '1.2.0', 'max_borglife': '1.5.0', 'deprecated': False},
        },
        'stripe': {
            '2.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.1.0', 'deprecated': True},
            '2.1.0': {'min_borglife': '1.0.0', 'max_borglife': '1.2.0', 'deprecated': False},
            '2.2.0': {'min_borglife': '1.1.0', 'max_borglife': '1.3.0', 'deprecated': False},
            '2.3.0': {'min_borglife': '1.2.0', 'max_borglife': '1.4.0', 'deprecated': False},
        },
        'bitcoin': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.3.0', 'deprecated': False},
            '1.1.0': {'min_borglife': '1.1.0', 'max_borglife': '1.4.0', 'deprecated': False},
        },
        'mongodb': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.2.0', 'deprecated': False},
            '1.1.0': {'min_borglife': '1.1.0', 'max_borglife': '1.3.0', 'deprecated': False},
        },
        'duckduckgo': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.4.0', 'deprecated': False},
        },
        'grafana': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.2.0', 'deprecated': False},
            '1.1.0': {'min_borglife': '1.1.0', 'max_borglife': '1.3.0', 'deprecated': False},
        },
        'wikipedia': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.4.0', 'deprecated': False},
        },
        'arxiv': {
            '1.0.0': {'min_borglife': '1.0.0', 'max_borglife': '1.3.0', 'deprecated': False},
            '1.1.0': {'min_borglife': '1.1.0', 'max_borglife': '1.4.0', 'deprecated': False},
        },
    }

    # Current Borglife version (would be dynamic in production)
    CURRENT_BORGLIFE_VERSION = "1.2.0"

    @classmethod
    def validate_compatibility(
        cls,
        organ_name: str,
        organ_version: str,
        borglife_version: str = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate if organ version is compatible with Borglife version

        Returns:
            (is_compatible: bool, reason: str, compatibility_info: dict)
        """
        if borglife_version is None:
            borglife_version = cls.CURRENT_BORGLIFE_VERSION

        # Check if organ exists in matrix
        if organ_name not in cls.COMPATIBILITY_MATRIX:
            return False, f"Organ '{organ_name}' not found in compatibility matrix", {}

        organ_matrix = cls.COMPATIBILITY_MATRIX[organ_name]

        # Check if organ version exists
        if organ_version not in organ_matrix:
            return False, f"Organ '{organ_name}' version '{organ_version}' not supported", {}

        compatibility = organ_matrix[organ_version]

        # Check if deprecated
        if compatibility.get('deprecated', False):
            return False, f"Organ '{organ_name}' version '{organ_version}' is deprecated", compatibility

        # Check version compatibility
        min_borglife = compatibility['min_borglife']
        max_borglife = compatibility['max_borglife']

        try:
            if not (semver.compare(min_borglife, borglife_version) <= 0 <= semver.compare(max_borglife, borglife_version)):
                return False, (
                    f"Organ '{organ_name}' v{organ_version} requires Borglife "
                    f"v{min_borglife} to v{max_borglife}, but running v{borglife_version}"
                ), compatibility
        except ValueError as e:
            return False, f"Version comparison error: {e}", compatibility

        return True, "Compatible", compatibility

    @classmethod
    def get_compatible_versions(
        cls,
        organ_name: str,
        borglife_version: str = None
    ) -> List[str]:
        """
        Get all organ versions compatible with current Borglife version

        Returns:
            List of compatible version strings, sorted by newest first
        """
        if borglife_version is None:
            borglife_version = cls.CURRENT_BORGLIFE_VERSION

        if organ_name not in cls.COMPATIBILITY_MATRIX:
            return []

        compatible_versions = []
        for version_str, compatibility in cls.COMPATIBILITY_MATRIX[organ_name].items():
            is_compatible, _, _ = cls.validate_compatibility(
                organ_name, version_str, borglife_version
            )
            if is_compatible:
                compatible_versions.append(version_str)

        # Sort by version (newest first)
        compatible_versions.sort(key=lambda v: semver.VersionInfo.parse(v), reverse=True)
        return compatible_versions

    @classmethod
    def get_recommended_version(cls, organ_name: str) -> Optional[str]:
        """
        Get recommended version for organ (newest non-deprecated)

        Returns:
            Recommended version string or None if no compatible versions
        """
        compatible = cls.get_compatible_versions(organ_name)
        if not compatible:
            return None

        # Return newest compatible version
        return compatible[0]

    @classmethod
    def check_update_available(
        cls,
        organ_name: str,
        current_version: str
    ) -> Tuple[bool, Optional[str], str]:
        """
        Check if update is available for organ

        Returns:
            (update_available: bool, new_version: str, reason: str)
        """
        recommended = cls.get_recommended_version(organ_name)
        if not recommended:
            return False, None, "No compatible versions found"

        try:
            if semver.compare(recommended, current_version) > 0:
                return True, recommended, f"Update available: {current_version} → {recommended}"
            else:
                return False, None, f"Already on latest compatible version: {current_version}"
        except ValueError:
            return False, None, f"Version comparison failed for {current_version} vs {recommended}"

    @classmethod
    def get_compatibility_report(
        cls,
        organ_versions: Dict[str, str],
        borglife_version: str = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compatibility report

        Args:
            organ_versions: {organ_name: current_version}

        Returns:
            {
                'overall_compatible': bool,
                'organ_reports': {organ_name: report},
                'summary': str
            }
        """
        if borglife_version is None:
            borglife_version = cls.CURRENT_BORGLIFE_VERSION

        organ_reports = {}
        overall_compatible = True

        for organ_name, current_version in organ_versions.items():
            is_compatible, reason, compatibility = cls.validate_compatibility(
                organ_name, current_version, borglife_version
            )

            update_available, new_version, update_reason = cls.check_update_available(
                organ_name, current_version
            )

            organ_reports[organ_name] = {
                'current_version': current_version,
                'compatible': is_compatible,
                'reason': reason,
                'compatibility': compatibility,
                'update_available': update_available,
                'recommended_version': new_version,
                'update_reason': update_reason
            }

            if not is_compatible:
                overall_compatible = False

        # Generate summary
        compatible_count = sum(1 for r in organ_reports.values() if r['compatible'])
        total_count = len(organ_reports)

        if overall_compatible:
            summary = f"All {total_count} organs compatible with Borglife v{borglife_version}"
        else:
            incompatible = [name for name, r in organ_reports.items() if not r['compatible']]
            summary = f"{len(incompatible)}/{total_count} organs incompatible: {', '.join(incompatible)}"

        return {
            'overall_compatible': overall_compatible,
            'organ_reports': organ_reports,
            'summary': summary,
            'borglife_version': borglife_version
        }