# BorgLife Scripts

This directory contains scripts for BorgLife Phase 1 operations, testing, and deployment.

## Path Configuration System

BorgLife uses a dynamic path resolution system to ensure portability across different environments. The system automatically detects installation paths and eliminates hard-coded paths.

### How It Works

1. **Environment Variables** (highest priority - **REQUIRED for production use**):
   ```bash
   export BORGLIFE_ROOT=/path/to/borglife
   export ARCHON_ROOT=/path/to/archon
   ```

2. **Auto-Detection** (fallback - may not work in all directory structures):
   - Detects BorgLife root from script location
   - Finds Archon root relative to BorgLife
   - Validates critical paths exist

3. **Configuration File** (lowest priority):
   - `.borglife_config` in BorgLife code directory
   - `$HOME/.borglife_config` for user-specific settings

### Required Environment Variables

**⚠️ IMPORTANT:** For production use, you **MUST** set the `BORGLIFE_ROOT` and `ARCHON_ROOT` environment variables. Auto-detection may fail in complex directory structures.

#### Setting Environment Variables

**Option 1: Temporary (current session only)**
```bash
export BORGLIFE_ROOT="/Users/m888888/borglife"
export ARCHON_ROOT="/Users/m888888/archon"
```

**Option 2: Persistent (add to your shell profile)**
```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
echo 'export BORGLIFE_ROOT="/Users/m888888/borglife"' >> ~/.bashrc
echo 'export ARCHON_ROOT="/Users/m888888/archon"' >> ~/.bashrc
source ~/.bashrc
```

**Option 3: Per-command execution**
```bash
BORGLIFE_ROOT="/Users/m888888/borglife" ARCHON_ROOT="/Users/m888888/archon" ./scripts/validate_demo_readiness.sh
```

#### Finding Your Paths

To determine the correct paths for your environment:

```bash
# Find BorgLife root (directory containing borglife_proto_private)
find /Users -name "borglife_proto_private" -type d 2>/dev/null | head -1 | xargs dirname

# Find Archon root (directory containing docker-compose.yml and python/)
find /Users -name "docker-compose.yml" -path "*/archon*" -type f 2>/dev/null | head -1 | xargs dirname
```

#### Verification

Test that your environment variables are set correctly:

```bash
source scripts/path_config.sh
echo "BORGLIFE_ROOT: $BORGLIFE_ROOT"
echo "ARCHON_ROOT: $ARCHON_ROOT"
echo "DOCKER_COMPOSE_FILE: $DOCKER_COMPOSE_FILE"
```

### Available Variables

After sourcing `path_config.sh`, these variables are available:

```bash
# Root directories
BORGLIFE_ROOT          # BorgLife installation root
ARCHON_ROOT           # Archon installation root

# Derived paths
DOCKER_COMPOSE_FILE   # Archon docker-compose.yml
BORGLIFE_CODE_DIR     # BorgLife code directory
BORGLIFE_TESTS_DIR    # Tests directory
BORGLIFE_SCRIPTS_DIR  # Scripts directory
```

### Usage in Scripts

```bash
#!/bin/bash
# Source path configuration
source "$(dirname "$0")/path_config.sh"

# Now use dynamic paths
echo "BorgLife root: $BORGLIFE_ROOT"
echo "Archon root: $ARCHON_ROOT"
echo "Docker compose: $DOCKER_COMPOSE_FILE"
```

### Configuration File Format

Create `.borglife_config` in the BorgLife code directory:

```bash
# BorgLife Configuration File
# BORGLIFE_ROOT=/custom/path/to/borglife
# ARCHON_ROOT=/custom/path/to/archon

# Service URLs
ARCHON_SERVER_URL=http://localhost:8181
ARCHON_MCP_URL=http://localhost:8051

# Test settings
E2E_TEST_TIMEOUT=300
LOG_LEVEL=INFO
```

### Error Handling

The system provides clear error messages for:
- Missing directories
- Invalid paths
- Permission issues
- Configuration conflicts

### Disabling Auto-Configuration

To disable automatic path configuration:

```bash
export BORGLIFE_DISABLE_AUTO_CONFIG=true
source scripts/path_config.sh
# Now manually set paths
export BORGLIFE_ROOT=/my/path
export ARCHON_ROOT=/my/archon/path
```

## Scripts Overview

### validate_demo_readiness.sh

Pre-demo validation script that checks:
- Environment setup
- Service health
- Test integrity
- Demo scenarios
- Performance benchmarks

**Usage:**
```bash
./scripts/validate_demo_readiness.sh [--quick] [--verbose] [--fix-issues]
```

### run_e2e_tests.sh

Complete end-to-end test execution script:
- Service startup and health checks
- Test execution with timeout
- Result reporting and cleanup

**Usage:**
```bash
./scripts/run_e2e_tests.sh [--no-docker] [--verbose] [--report-only]
```

### path_config.sh

Path configuration and resolution system (see above).

## Troubleshooting

### Common Issues

1. **"Could not detect Archon root directory"**
   - Ensure Archon is installed alongside BorgLife
   - Check directory structure: `borglife/` and `archon/` should be siblings
   - Set `ARCHON_ROOT` environment variable manually

2. **"BorgLife root directory not found"**
   - Verify script is run from correct location
   - Check that BorgLife directory structure is intact
   - Set `BORGLIFE_ROOT` environment variable manually

3. **Permission denied errors**
   - Ensure user has read access to all directories
   - Check file permissions on configuration files

### Troubleshooting Environment Variables

#### Problem: "Could not detect Archon root directory"

**Solution:** Set environment variables explicitly:
```bash
export BORGLIFE_ROOT="/Users/m888888/borglife"
export ARCHON_ROOT="/Users/m888888/archon"
```

#### Problem: "BorgLife root directory not found"

**Solution:** Verify the path exists and set BORGLIFE_ROOT:
```bash
ls -la "$BORGLIFE_ROOT/borglife_proto_private"
# If this fails, find the correct path:
find /Users -name "borglife_proto_private" -type d 2>/dev/null
```

#### Problem: Scripts fail with path errors

**Solution:** Always set environment variables before running scripts:
```bash
BORGLIFE_ROOT="/path/to/borglife" ARCHON_ROOT="/path/to/archon" ./scripts/validate_demo_readiness.sh
```

### Debug Mode

Enable verbose logging:

```bash
export BORGLIFE_DEBUG=true
source scripts/path_config.sh
```

## Development

When adding new scripts:

1. Source `path_config.sh` at the top
2. Use provided path variables instead of hard-coded paths
3. Add documentation to this README
4. Test in different directory structures