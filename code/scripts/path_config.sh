#!/bin/bash
# BorgLife Path Configuration System
#
# This script provides dynamic path resolution for BorgLife and Archon integration.
# It eliminates hard-coded paths and ensures portability across different environments.
#
# Usage: source scripts/path_config.sh
# Then use variables: $BORGLIFE_ROOT, $ARCHON_ROOT, $DOCKER_COMPOSE_FILE, etc.

# Configuration priority:
# 1. Environment variables (highest priority)
# 2. Auto-detection from script location
# 3. Config file fallback (lowest priority)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[PATH_CONFIG]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[PATH_CONFIG WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[PATH_CONFIG ERROR]${NC} $1" >&2
}

# Get script directory (works when sourced or executed)
get_script_dir() {
    if [[ -n "${BASH_SOURCE[0]}" ]]; then
        # Script is being sourced or executed directly
        echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        # Fallback for edge cases
        echo "$(pwd)"
    fi
}

# Validate directory exists and is readable
validate_directory() {
    local dir_path="$1"
    local dir_name="$2"

    if [[ ! -d "$dir_path" ]]; then
        log_error "$dir_name directory not found: $dir_path"
        return 1
    fi

    if [[ ! -r "$dir_path" ]]; then
        log_error "$dir_name directory not readable: $dir_path"
        return 1
    fi

    return 0
}

# Detect BorgLife root from script location
detect_borglife_root() {
    local script_dir
    script_dir="$(get_script_dir)"

    # BorgLife structure: borglife/borglife_proto_private/code/scripts/
    # So borglife root is 3 levels up from scripts/
    local borglife_root
    borglife_root="$(cd "$script_dir/../../.." && pwd)"

    if validate_directory "$borglife_root" "BorgLife root"; then
        echo "$borglife_root"
        return 0
    else
        return 1
    fi
}

# Detect Archon root relative to BorgLife
detect_archon_root() {
    local borglife_root="$1"

    # Archon is typically at the same level as borglife directory
    # borglife/ -> ../archon/
    local archon_root
    archon_root="$(cd "$borglife_root/../archon" && pwd)"

    # Look for archon indicators
    if [[ -f "$archon_root/docker-compose.yml" ]] && [[ -d "$archon_root/python" ]]; then
        if validate_directory "$archon_root" "Archon root"; then
            echo "$archon_root"
            return 0
        fi
    fi

    # Fallback: check if current directory is archon
    if [[ -f "docker-compose.yml" ]] && [[ -d "python" ]]; then
        archon_root="$(pwd)"
        if validate_directory "$archon_root" "Archon root (current dir)"; then
            echo "$archon_root"
            return 0
        fi
    fi

    log_error "Could not detect Archon root directory"
    return 1
}

# Load configuration from file if it exists
load_config_file() {
    local config_file="$1"

    if [[ -f "$config_file" ]] && [[ -r "$config_file" ]]; then
        log_info "Loading configuration from: $config_file"

        # Source the config file (bash variables)
        # shellcheck disable=SC1090
        source "$config_file"
        return 0
    fi

    return 1
}

# Main path configuration function
configure_paths() {
    log_info "Initializing BorgLife path configuration..."

    # 1. Try environment variables first (highest priority)
    if [[ -n "${BORGLIFE_ROOT:-}" ]]; then
        log_info "Using BORGLIFE_ROOT from environment: $BORGLIFE_ROOT"
        export BORGLIFE_ROOT="$BORGLIFE_ROOT"
    else
        # Auto-detect BorgLife root
        if BORGLIFE_ROOT="$(detect_borglife_root)"; then
            log_info "Auto-detected BORGLIFE_ROOT: $BORGLIFE_ROOT"
            export BORGLIFE_ROOT="$BORGLIFE_ROOT"
        else
            log_error "Failed to determine BORGLIFE_ROOT"
            return 1
        fi
    fi

    # 2. Try environment variables for Archon
    if [[ -n "${ARCHON_ROOT:-}" ]]; then
        log_info "Using ARCHON_ROOT from environment: $ARCHON_ROOT"
        export ARCHON_ROOT="$ARCHON_ROOT"
    else
        # Auto-detect Archon root
        if ARCHON_ROOT="$(detect_archon_root "$BORGLIFE_ROOT")"; then
            log_info "Auto-detected ARCHON_ROOT: $ARCHON_ROOT"
            export ARCHON_ROOT="$ARCHON_ROOT"
        else
            log_error "Failed to determine ARCHON_ROOT"
            return 1
        fi
    fi

    # 3. Set derived paths
    export DOCKER_COMPOSE_FILE="$ARCHON_ROOT/docker-compose.yml"
    export BORGLIFE_CODE_DIR="$BORGLIFE_ROOT/borglife_proto_private/code"
    export BORGLIFE_TESTS_DIR="$BORGLIFE_CODE_DIR/tests"
    export BORGLIFE_SCRIPTS_DIR="$BORGLIFE_CODE_DIR/scripts"

    # 4. Validate critical paths exist
    local critical_paths=(
        "$BORGLIFE_ROOT:BorgLife root"
        "$ARCHON_ROOT:Archon root"
        "$DOCKER_COMPOSE_FILE:Docker Compose file"
        "$BORGLIFE_CODE_DIR:BorgLife code directory"
    )

    for path_info in "${critical_paths[@]}"; do
        IFS=':' read -r path_value path_name <<< "$path_info"
        if ! validate_directory "$path_value" "$path_name" 2>/dev/null; then
            # Try as file for docker-compose.yml
            if [[ ! -f "$path_value" ]]; then
                log_error "Critical path validation failed: $path_name ($path_value)"
                return 1
            fi
        fi
    done

    # 5. Load additional config if available
    local config_files=(
        "$BORGLIFE_ROOT/.borglife_config"
        "$BORGLIFE_CODE_DIR/.borglife_config"
        "$HOME/.borglife_config"
    )

    for config_file in "${config_files[@]}"; do
        if load_config_file "$config_file"; then
            break
        fi
    done

    log_info "Path configuration completed successfully"
    log_info "  BORGLIFE_ROOT: $BORGLIFE_ROOT"
    log_info "  ARCHON_ROOT: $ARCHON_ROOT"
    log_info "  DOCKER_COMPOSE_FILE: $DOCKER_COMPOSE_FILE"

    return 0
}

# Export the main function so it can be called when sourced
export -f configure_paths
export -f get_script_dir
export -f validate_directory
export -f detect_borglife_root
export -f detect_archon_root
export -f load_config_file

# Auto-configure when sourced (unless disabled)
if [[ "${BORGLIFE_DISABLE_AUTO_CONFIG:-false}" != "true" ]]; then
    if ! configure_paths; then
        log_error "Failed to configure paths automatically"
        log_error "Set BORGLIFE_ROOT and ARCHON_ROOT environment variables manually"
        return 1 2>/dev/null || exit 1
    fi
fi