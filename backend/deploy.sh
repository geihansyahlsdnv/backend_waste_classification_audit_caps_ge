#!/bin/bash

# Waste Classification Backend - Quick Deployment Script
# Usage: bash deploy.sh [init|start|stop|restart|logs|status]

set -e

PROJECT_NAME="Waste Classification Backend"
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
  echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
  echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[!]${NC} $1"
}

print_header() {
  echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Check if Docker is installed
check_docker() {
  if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
  fi
  if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
  fi
  print_status "Docker and Docker Compose found"
}

# Check environment file
check_env() {
  if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file not found: $ENV_FILE"
    print_warning "Creating from .env.production..."
    if [ -f ".env.production" ]; then
      cp .env.production "$ENV_FILE"
      print_status "Environment file created from .env.production"
      print_warning "Please update sensitive values in .env file before deploying"
      exit 1
    else
      print_error "Template file .env.production not found either"
      exit 1
    fi
  fi
  print_status "Environment file found"
}

# Initialize deployment
init_deployment() {
  print_header "Initializing Deployment"
  
  check_docker
  check_env
  
  # Check for SSL certificates
  if [ ! -d "ssl" ]; then
    print_warning "SSL directory not found. Creating..."
    mkdir -p ssl
  fi
  
  if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    print_error "SSL certificates not found!"
    print_warning "Please run Let's Encrypt setup first:"
    echo "  sudo certbot certonly --standalone -d hargai.site"
    echo "  sudo cp /etc/letsencrypt/live/hargai.site/fullchain.pem ./ssl/cert.pem"
    echo "  sudo cp /etc/letsencrypt/live/hargai.site/privkey.pem ./ssl/key.pem"
    echo "  sudo chown \$USER:\$USER ./ssl/*.pem"
    exit 1
  fi
  print_status "SSL certificates found"
  
  # Check Nginx config
  if [ ! -f "nginx.conf" ]; then
    print_error "nginx.conf not found!"
    exit 1
  fi
  print_status "Nginx configuration found"
  
  # Create uploads directory
  mkdir -p uploads
  print_status "Uploads directory ready"
  
  print_header "Initialization Complete"
  echo "Next steps:"
  echo "  1. Review and update sensitive values in .env"
  echo "  2. Run: bash deploy.sh start"
}

# Start services
start_services() {
  print_header "Starting Services"
  
  check_env
  
  docker-compose -f "$COMPOSE_FILE" up -d
  
  print_status "Services starting..."
  
  # Wait for services to be ready
  print_warning "Waiting for services to be healthy..."
  sleep 5
  
  # Check health
  max_attempts=30
  attempt=0
  while [ $attempt -lt $max_attempts ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
      print_status "Backend is healthy"
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
      print_error "Backend health check failed after ${max_attempts}0 seconds"
      print_warning "Check logs with: bash deploy.sh logs"
      exit 1
    fi
    sleep 1
  done
  
  print_header "Deployment Summary"
  docker-compose -f "$COMPOSE_FILE" ps
  
  echo ""
  echo "Service URLs:"
  echo "  API: https://hargai.site"
  echo "  Health: https://hargai.site/health"
  echo "  Docs: https://hargai.site/docs"
  echo "  MinIO Console: https://hargai.site:9001 (via SSH tunnel)"
  echo ""
  echo "View logs: bash deploy.sh logs"
}

# Stop services
stop_services() {
  print_header "Stopping Services"
  
  docker-compose -f "$COMPOSE_FILE" down
  
  print_status "Services stopped"
}

# Restart services
restart_services() {
  print_header "Restarting Services"
  
  docker-compose -f "$COMPOSE_FILE" restart
  
  sleep 3
  
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Services restarted successfully"
  else
    print_error "Services may not be healthy"
  fi
}

# Show logs
show_logs() {
  print_header "Service Logs"
  
  # Show last 50 lines or follow
  if [ -z "$1" ]; then
    docker-compose -f "$COMPOSE_FILE" logs --tail=50
  else
    docker-compose -f "$COMPOSE_FILE" logs -f
  fi
}

# Show status
show_status() {
  print_header "Service Status"
  
  docker-compose -f "$COMPOSE_FILE" ps
  
  echo ""
  print_header "System Health"
  
  # API health
  if curl -sf https://hargai.site/health > /dev/null 2>&1; then
    print_status "API is healthy"
  else
    print_error "API health check failed"
  fi
  
  # Database check
  if docker-compose -f "$COMPOSE_FILE" exec -T db psql -U waste_user -d waste_db -c "SELECT 1" > /dev/null 2>&1; then
    print_status "Database is connected"
  else
    print_error "Database connection failed"
  fi
  
  echo ""
  print_header "Resource Usage"
  docker stats --no-stream waste-classifier-backend waste-classifier-db waste-classifier-redis 2>/dev/null || print_warning "Could not retrieve resource usage"
}

# Print usage
print_usage() {
  echo "Waste Classification Backend - Deployment Script"
  echo ""
  echo "Usage: bash deploy.sh [COMMAND]"
  echo ""
  echo "Commands:"
  echo "  init      - Initialize deployment (first run)"
  echo "  start     - Start all services"
  echo "  stop      - Stop all services"
  echo "  restart   - Restart all services"
  echo "  logs      - Show service logs (add -f to follow)"
  echo "  status    - Show service status and health"
  echo "  help      - Show this help message"
  echo ""
  echo "Examples:"
  echo "  bash deploy.sh init                # First time setup"
  echo "  bash deploy.sh start               # Start deployment"
  echo "  bash deploy.sh logs -f             # Follow logs"
  echo "  bash deploy.sh status              # Check status"
}

# Main script logic
case "${1:-help}" in
  init)
    init_deployment
    ;;
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  restart)
    restart_services
    ;;
  logs)
    show_logs "$2"
    ;;
  status)
    show_status
    ;;
  help)
    print_usage
    ;;
  *)
    print_error "Unknown command: $1"
    echo ""
    print_usage
    exit 1
    ;;
esac
