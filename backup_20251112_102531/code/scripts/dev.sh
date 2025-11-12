#!/bin/bash
# borglife_prototype/scripts/dev.sh
# Unified development startup script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
PROJECT_NAME="borglife"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed."
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed."
        exit 1
    fi

    log_success "Dependencies check passed"
}

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file '$ENV_FILE' not found."
        log_info "Creating template environment file..."

        cat > "$ENV_FILE" << EOF
# BorgLife Environment Configuration
# Copy this file and fill in your actual values

# Supabase Configuration (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key

# OpenAI Configuration (Required)
OPENAI_API_KEY=your-openai-api-key

# Optional: External Service Credentials
GMAIL_CREDENTIALS=base64-encoded-gmail-credentials
STRIPE_SECRET_KEY=your-stripe-secret-key
MONGODB_CONNECTION_STRING=mongodb://username:password@host:port/database

# Local Development
POSTGRES_PASSWORD=secure-postgres-password
JAM_MOCK_MODE=true

# BorgLife Configuration
BORGLIFE_UI_PORT=8501
BORGLIFE_MCP_PORT=8053
BORGLIFE_AGENT_PORT=8054
EOF

        log_warning "Please edit '$ENV_FILE' with your actual configuration values."
        log_info "Then run this script again."
        exit 1
    fi

    # Validate required environment variables
    required_vars=("SUPABASE_URL" "SUPABASE_SERVICE_KEY" "OPENAI_API_KEY")
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=your-" "$ENV_FILE"; then
            log_error "Required environment variable '$var' is not set in '$ENV_FILE'"
            exit 1
        fi
    done

    log_success "Environment configuration validated"
}

setup_python_env() {
    log_info "Setting up Python environment..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "Created virtual environment"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install/update dependencies
    pip install --upgrade pip
    pip install -r requirements.txt

    log_success "Python environment ready"
}

start_services() {
    local mode="$1"

    log_info "Starting BorgLife services in $mode mode..."

    case "$mode" in
        "full")
            # Start all services including Docker MCP organs
            docker-compose --project-name "$PROJECT_NAME" up -d
            docker-compose --project-name "$PROJECT_NAME" --profile organs up -d
            ;;
        "core")
            # Start only core services (no Docker MCP organs)
            docker-compose --project-name "$PROJECT_NAME" up -d borglife-ui borglife-mcp borglife-agent archon-server archon-mcp archon-agents redis
            ;;
        "minimal")
            # Start only UI and essential services
            docker-compose --project-name "$PROJECT_NAME" up -d borglife-ui archon-server redis
            ;;
        *)
            log_error "Invalid mode: $mode"
            show_usage
            exit 1
            ;;
    esac

    log_success "Services starting up..."
    log_info "This may take a few minutes for the first run"
}

wait_for_services() {
    log_info "Waiting for services to be ready..."

    # Wait for Archon server
    log_info "Waiting for Archon server..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8181/health > /dev/null 2>&1; then
            log_success "Archon server is ready"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done

    if [ $timeout -le 0 ]; then
        log_warning "Archon server health check timed out"
    fi

    # Wait for BorgLife UI
    log_info "Waiting for BorgLife UI..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8501 > /dev/null 2>&1; then
            log_success "BorgLife UI is ready"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done

    if [ $timeout -le 0 ]; then
        log_warning "BorgLife UI health check timed out"
    fi
}

show_status() {
    log_info "Service Status:"

    echo ""
    echo "BorgLife Services:"
    echo "  🤖 UI:        http://localhost:8501"
    echo "  🔧 MCP:       http://localhost:8053"
    echo "  🧠 Agent:     http://localhost:8054"
    echo ""

    echo "Archon Services:"
    echo "  🏠 Server:    http://localhost:8181"
    echo "  🔌 MCP:       http://localhost:8051"
    echo "  🤖 Agents:    http://localhost:8052"
    echo ""

    echo "Docker MCP Organs:"
    echo "  📧 Gmail:     http://localhost:8081"
    echo "  💳 Stripe:    http://localhost:8082"
    echo "  🍃 MongoDB:   http://localhost:8083"
    echo "  🦆 DuckGo:    http://localhost:8084"
    echo ""

    log_info "To view logs: docker-compose logs -f [service-name]"
    log_info "To stop: docker-compose down"
}

show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start [mode]    Start services (modes: full, core, minimal)"
    echo "  stop            Stop all services"
    echo "  restart [mode]  Restart services"
    echo "  logs [service]  Show logs for service (or all)"
    echo "  status          Show service status"
    echo "  clean           Remove containers and volumes"
    echo "  setup           Initial setup and validation"
    echo ""
    echo "Modes:"
    echo "  full    - All services including Docker MCP organs"
    echo "  core    - Core services only (default)"
    echo "  minimal - UI and essential services only"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start core services"
    echo "  $0 start full     # Start all services"
    echo "  $0 logs borglife-ui  # Show UI logs"
    echo "  $0 stop           # Stop all services"
}

# Main script logic
case "${1:-start}" in
    "start")
        mode="${2:-core}"
        check_dependencies
        check_env_file
        setup_python_env
        start_services "$mode"
        wait_for_services
        show_status
        ;;
    "stop")
        log_info "Stopping services..."
        docker-compose --project-name "$PROJECT_NAME" down
        log_success "Services stopped"
        ;;
    "restart")
        mode="${2:-core}"
        log_info "Restarting services..."
        docker-compose --project-name "$PROJECT_NAME" down
        start_services "$mode"
        wait_for_services
        show_status
        ;;
    "logs")
        service="${2:-}"
        if [ -n "$service" ]; then
            docker-compose --project-name "$PROJECT_NAME" logs -f "$service"
        else
            docker-compose --project-name "$PROJECT_NAME" logs -f
        fi
        ;;
    "status")
        show_status
        ;;
    "clean")
        log_warning "This will remove all containers and volumes!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose --project-name "$PROJECT_NAME" down -v --remove-orphans
            docker system prune -f
            log_success "Cleanup completed"
        fi
        ;;
    "setup")
        check_dependencies
        check_env_file
        setup_python_env
        log_success "Setup completed"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac