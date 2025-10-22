# borglife_prototype/archon_adapter/version.py
"""
Version compatibility management for Archon services.

Ensures Borglife can work with different versions of Archon
and provides feature detection capabilities.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from packaging import version

from .exceptions import VersionCompatibilityError

logger = logging.getLogger(__name__)

class VersionCompatibility:
    """Manages version compatibility between Borglife and Archon."""

    # Minimum and maximum supported Archon versions
    MIN_SUPPORTED_VERSION = "0.1.0"
    MAX_SUPPORTED_VERSION = "0.2.0"

    # Feature availability by version
    FEATURE_MATRIX = {
        'rag_query': {
            'min_version': '0.1.0',
            'description': 'RAG query functionality'
        },
        'task_management': {
            'min_version': '0.1.5',
            'description': 'Task creation and management'
        },
        'code_examples': {
            'min_version': '0.1.8',
            'description': 'Code example search'
        },
        'streaming_agents': {
            'min_version': '0.1.2',
            'description': 'Streaming agent responses'
        },
        'mcp_tools': {
            'min_version': '0.1.0',
            'description': 'MCP tool invocation'
        },
        'health_checks': {
            'min_version': '0.1.0',
            'description': 'Service health endpoints'
        },
        'project_management': {
            'min_version': '0.1.3',
            'description': 'Project CRUD operations'
        }
    }

    def __init__(self):
        self.checked_versions = {}

    def validate_version(self, service: str, current_version: str) -> bool:
        """
        Validate if a service version is compatible.

        Args:
            service: Service name (e.g., 'archon-server')
            current_version: Current version string

        Returns:
            True if compatible

        Raises:
            VersionCompatibilityError: If version is incompatible
        """
        try:
            current = version.parse(current_version)
            min_supported = version.parse(self.MIN_SUPPORTED_VERSION)
            max_supported = version.parse(self.MAX_SUPPORTED_VERSION)

            if not (min_supported <= current <= max_supported):
                raise VersionCompatibilityError(
                    service=service,
                    current_version=current_version,
                    required_version=f"{self.MIN_SUPPORTED_VERSION} - {self.MAX_SUPPORTED_VERSION}"
                )

            self.checked_versions[service] = current_version
            logger.info(f"{service} version {current_version} is compatible")
            return True

        except version.InvalidVersion as e:
            logger.error(f"Invalid version format for {service}: {current_version}")
            raise VersionCompatibilityError(
                service=service,
                current_version=current_version,
                required_version="valid semver format"
            )

    def supports_feature(self, feature: str, service_version: Optional[str] = None) -> bool:
        """
        Check if a feature is supported in the given version.

        Args:
            feature: Feature name
            service_version: Version to check (uses latest checked if None)

        Returns:
            True if feature is supported
        """
        if feature not in self.FEATURE_MATRIX:
            logger.warning(f"Unknown feature: {feature}")
            return False

        if service_version is None:
            # Use the most recent version check
            service_version = self._get_latest_version()

        if not service_version:
            return False

        try:
            current = version.parse(service_version)
            min_required = version.parse(self.FEATURE_MATRIX[feature]['min_version'])

            return current >= min_required

        except version.InvalidVersion:
            return False

    def get_feature_requirements(self, feature: str) -> Dict[str, str]:
        """
        Get version requirements for a feature.

        Args:
            feature: Feature name

        Returns:
            Feature requirements dict
        """
        return self.FEATURE_MATRIX.get(feature, {})

    def get_supported_features(self, service_version: str) -> List[str]:
        """
        Get all features supported by a version.

        Args:
            service_version: Version to check

        Returns:
            List of supported feature names
        """
        supported = []

        for feature, requirements in self.FEATURE_MATRIX.items():
            if self.supports_feature(feature, service_version):
                supported.append(feature)

        return supported

    def get_minimum_version_for_features(self, features: List[str]) -> Optional[str]:
        """
        Get minimum version required for a set of features.

        Args:
            features: List of feature names

        Returns:
            Minimum version string or None if features unknown
        """
        if not features:
            return self.MIN_SUPPORTED_VERSION

        max_min_version = None

        for feature in features:
            if feature not in self.FEATURE_MATRIX:
                logger.warning(f"Unknown feature for version check: {feature}")
                continue

            feature_min = self.FEATURE_MATRIX[feature]['min_version']

            if max_min_version is None:
                max_min_version = feature_min
            else:
                try:
                    current_max = version.parse(max_min_version)
                    feature_ver = version.parse(feature_min)
                    if feature_ver > current_max:
                        max_min_version = feature_min
                except version.InvalidVersion:
                    continue

        return max_min_version or self.MIN_SUPPORTED_VERSION

    def get_version_info(self) -> Dict[str, Any]:
        """
        Get comprehensive version information.

        Returns:
            Version compatibility information
        """
        return {
            'supported_range': {
                'min': self.MIN_SUPPORTED_VERSION,
                'max': self.MAX_SUPPORTED_VERSION
            },
            'features': self.FEATURE_MATRIX,
            'checked_versions': self.checked_versions.copy(),
            'latest_version': self._get_latest_version()
        }

    def _get_latest_version(self) -> Optional[str]:
        """Get the most recently checked version."""
        if not self.checked_versions:
            return None

        # Return version from most recently checked service
        return list(self.checked_versions.values())[-1]

    def check_feature_compatibility(
        self,
        required_features: List[str],
        available_version: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if version supports all required features.

        Args:
            required_features: Features that must be supported
            available_version: Version to check against

        Returns:
            (is_compatible: bool, missing_features: list)
        """
        missing_features = []

        for feature in required_features:
            if not self.supports_feature(feature, available_version):
                missing_features.append(feature)

        return len(missing_features) == 0, missing_features

    def get_upgrade_recommendations(self, current_version: str) -> Dict[str, Any]:
        """
        Get recommendations for version upgrades.

        Args:
            current_version: Current version

        Returns:
            Upgrade recommendations
        """
        try:
            current = version.parse(current_version)
            max_supported = version.parse(self.MAX_SUPPORTED_VERSION)

            recommendations = {
                'current_version': current_version,
                'is_latest_supported': current >= max_supported,
                'new_features_available': [],
                'recommended_upgrade': None
            }

            if current < max_supported:
                # Find features not available in current version
                for feature, requirements in self.FEATURE_MATRIX.items():
                    if not self.supports_feature(feature, current_version):
                        recommendations['new_features_available'].append({
                            'feature': feature,
                            'description': requirements['description'],
                            'available_from': requirements['min_version']
                        })

                recommendations['recommended_upgrade'] = self.MAX_SUPPORTED_VERSION

            return recommendations

        except version.InvalidVersion:
            return {
                'error': f'Invalid version format: {current_version}',
                'current_version': current_version
            }