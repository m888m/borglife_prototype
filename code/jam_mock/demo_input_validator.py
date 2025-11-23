"""
Input Validation for BorgLife Demo
Comprehensive validation of all demo inputs for security and integrity.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import yaml


class DemoInputValidator:
    """Validate all demo inputs for security and integrity"""

    # Security patterns
    MALICIOUS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"eval\s*\(",
        r"document\.",
        r"window\.",
        r"alert\s*\(",
        r"prompt\s*\(",
        r"confirm\s*\(",
        r"console\.",
        r"process\.",
        r"os\.",
        r"subprocess",
        r"import\s+os",
        r"import\s+subprocess",
        r"exec\s*\(",
        r"system\s*\(",
        r"popen\s*\(",
    ]

    # Valid DNA structure patterns
    VALID_DNA_KEYS = {
        "borg_id",
        "version",
        "cells",
        "organs",
        "phenotype",
        "metadata",
        "created_at",
        "updated_at",
    }

    VALID_CELL_KEYS = {"id", "type", "properties", "connections"}
    VALID_ORGAN_KEYS = {"id", "type", "cells", "function", "properties"}

    def __init__(self):
        self.validation_errors = []

    def validate_task_description(self, task: str) -> Dict[str, Any]:
        """Validate task description for malicious content and format"""
        result = {"valid": True, "errors": [], "warnings": [], "sanitized_task": task}

        if not task or not isinstance(task, str):
            result["valid"] = False
            result["errors"].append("Task description must be a non-empty string")
            return result

        # Length validation
        if len(task) > 1000:
            result["valid"] = False
            result["errors"].append("Task description too long (max 1000 characters)")
            return result

        # Check for malicious patterns
        for pattern in self.MALICIOUS_PATTERNS:
            if re.search(pattern, task, re.IGNORECASE):
                result["valid"] = False
                result["errors"].append(f"Malicious content detected: {pattern}")
                return result

        # Check for potentially harmful keywords
        harmful_keywords = ["rm ", "del ", "format ", "drop ", "delete "]
        for keyword in harmful_keywords:
            if keyword.lower() in task.lower():
                result["warnings"].append(
                    f"Potentially harmful keyword detected: {keyword.strip()}"
                )

        # Sanitize task
        result["sanitized_task"] = self._sanitize_text(task)

        return result

    def validate_dna_config(self, dna_yaml: str) -> Dict[str, Any]:
        """Validate DNA configuration for integrity and security"""
        result = {"valid": True, "errors": [], "warnings": [], "parsed_dna": None}

        try:
            # Parse YAML safely
            dna_data = yaml.safe_load(dna_yaml)
            if not dna_data or not isinstance(dna_data, dict):
                result["valid"] = False
                result["errors"].append("Invalid DNA format: must be valid YAML object")
                return result

            # Validate top-level structure
            self._validate_dna_structure(dna_data, result)

            # Validate cells
            if "cells" in dna_data:
                self._validate_cells(dna_data["cells"], result)

            # Validate organs
            if "organs" in dna_data:
                self._validate_organs(dna_data["organs"], result)

            # Store parsed DNA if valid
            if result["valid"]:
                result["parsed_dna"] = dna_data

        except yaml.YAMLError as e:
            result["valid"] = False
            result["errors"].append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Validation error: {str(e)}")

        return result

    def validate_cost_limit(
        self, cost: Any, max_limit: Decimal = Decimal("1.0")
    ) -> Dict[str, Any]:
        """Validate cost values for budget control"""
        result = {"valid": True, "errors": [], "cost_decimal": None}

        try:
            if isinstance(cost, str):
                cost_decimal = Decimal(cost)
            elif isinstance(cost, (int, float)):
                cost_decimal = Decimal(str(cost))
            elif isinstance(cost, Decimal):
                cost_decimal = cost
            else:
                result["valid"] = False
                result["errors"].append("Cost must be numeric")
                return result

            if cost_decimal < 0:
                result["valid"] = False
                result["errors"].append("Cost cannot be negative")
                return result

            if cost_decimal > max_limit:
                result["valid"] = False
                result["errors"].append(f"Cost exceeds maximum limit of {max_limit}")
                return result

            result["cost_decimal"] = cost_decimal

        except (InvalidOperation, ValueError) as e:
            result["valid"] = False
            result["errors"].append(f"Invalid cost format: {str(e)}")

        return result

    def validate_address(
        self, address: str, network: str = "westend"
    ) -> Dict[str, Any]:
        """Validate blockchain address format"""
        result = {"valid": True, "errors": [], "address_type": None}

        if not address or not isinstance(address, str):
            result["valid"] = False
            result["errors"].append("Address must be a non-empty string")
            return result

        # Basic SS58 address validation (starts with network prefix)
        if network == "westend":
            if not address.startswith("5"):  # Westend addresses start with '5'
                result["valid"] = False
                result["errors"].append("Invalid Westend address format")
        elif network == "kusama":
            if not address.startswith(
                ("C", "D", "F", "G", "H", "J")
            ):  # Kusama prefixes
                result["valid"] = False
                result["errors"].append("Invalid Kusama address format")

        # Length validation (SS58 addresses are ~40-50 characters)
        if len(address) < 30 or len(address) > 60:
            result["valid"] = False
            result["errors"].append("Address length invalid")

        # Check for malicious patterns
        for pattern in self.MALICIOUS_PATTERNS:
            if re.search(pattern, address, re.IGNORECASE):
                result["valid"] = False
                result["errors"].append("Malicious content in address")
                break

        if result["valid"]:
            result["address_type"] = network

        return result

    def _validate_dna_structure(self, dna_data: Dict, result: Dict):
        """Validate top-level DNA structure"""
        # Check required fields
        if "borg_id" not in dna_data:
            result["valid"] = False
            result["errors"].append("Missing required field: borg_id")

        # Validate borg_id format
        if "borg_id" in dna_data:
            borg_id = dna_data["borg_id"]
            if not isinstance(borg_id, str) or len(borg_id) > 100:
                result["valid"] = False
                result["errors"].append("borg_id must be string, max 100 characters")

        # Check for unknown top-level keys
        for key in dna_data.keys():
            if key not in self.VALID_DNA_KEYS:
                result["warnings"].append(f"Unknown DNA key: {key}")

    def _validate_cells(self, cells: Any, result: Dict):
        """Validate cells structure"""
        if not isinstance(cells, list):
            result["valid"] = False
            result["errors"].append("cells must be a list")
            return

        for i, cell in enumerate(cells):
            if not isinstance(cell, dict):
                result["valid"] = False
                result["errors"].append(f"Cell {i} must be an object")
                continue

            # Validate cell structure
            for key in cell.keys():
                if key not in self.VALID_CELL_KEYS:
                    result["warnings"].append(f"Unknown cell key in cell {i}: {key}")

    def _validate_organs(self, organs: Any, result: Dict):
        """Validate organs structure"""
        if not isinstance(organs, list):
            result["valid"] = False
            result["errors"].append("organs must be a list")
            return

        for i, organ in enumerate(organs):
            if not isinstance(organ, dict):
                result["valid"] = False
                result["errors"].append(f"Organ {i} must be an object")
                continue

            # Validate organ structure
            for key in organ.keys():
                if key not in self.VALID_ORGAN_KEYS:
                    result["warnings"].append(f"Unknown organ key in organ {i}: {key}")

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text input"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[<>]", "", text)
        # Trim whitespace
        return sanitized.strip()

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation results"""
        return {
            "total_validations": len(self.validation_errors),
            "errors": self.validation_errors.copy(),
            "last_validation_time": datetime.utcnow().isoformat(),
        }
