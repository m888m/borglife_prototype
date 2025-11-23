"""
Synthesis Module Exceptions

Custom exceptions for the BorgLife synthesis pipeline.
"""


class SynthesisError(Exception):
    """Base exception for synthesis module errors."""

    def __init__(self, message: str, borg_id: str = None):
        self.borg_id = borg_id
        self.message = message
        super().__init__(f"Borg {borg_id}: {message}" if borg_id else message)


class DNAParseError(SynthesisError):
    """Raised when DNA parsing fails."""

    def __init__(self, message: str, yaml_content: str = None):
        super().__init__(message)
        self.yaml_content = yaml_content


class DNAValidationError(SynthesisError):
    """Raised when DNA validation fails."""

    def __init__(self, borg_id: str, validation_errors: list):
        self.validation_errors = validation_errors
        error_msg = f"DNA validation failed: {'; '.join(validation_errors)}"
        super().__init__(error_msg, borg_id)


class PhenotypeBuildError(SynthesisError):
    """Raised when phenotype building fails."""

    def __init__(self, borg_id: str, message: str):
        super().__init__(message, borg_id)


class OrganInjectionError(SynthesisError):
    """Raised when organ injection fails."""

    def __init__(self, borg_id: str, organ_name: str, message: str):
        self.organ_name = organ_name
        error_msg = f"Organ injection failed for '{organ_name}': {message}"
        super().__init__(error_msg, borg_id)


class CellExecutionError(SynthesisError):
    """Raised when cell execution fails."""

    def __init__(self, borg_id: str, cell_name: str, message: str):
        self.cell_name = cell_name
        error_msg = f"Cell execution failed for '{cell_name}': {message}"
        super().__init__(error_msg, borg_id)


class CostCalculationError(SynthesisError):
    """Raised when cost calculation fails."""

    def __init__(self, borg_id: str, message: str):
        super().__init__(message, borg_id)


class EncodingError(SynthesisError):
    """Raised when phenotype encoding fails."""

    def __init__(self, borg_id: str, message: str):
        super().__init__(message, borg_id)


class IntegrityError(SynthesisError):
    """Raised when data integrity checks fail."""

    def __init__(
        self,
        borg_id: str,
        message: str,
        expected_hash: str = None,
        actual_hash: str = None,
    ):
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        error_msg = f"Integrity check failed: {message}"
        if expected_hash and actual_hash:
            error_msg += (
                f" (expected: {expected_hash[:16]}..., actual: {actual_hash[:16]}...)"
            )
        super().__init__(error_msg, borg_id)
