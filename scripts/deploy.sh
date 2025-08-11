#!/bin/bash

# My Newsletters Voice Assistant - Production Deployment Script
# This script deploys the application to production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
DEPLOY_BRANCH=${2:-main}

echo -e "${GREEN}Starting deployment to ${ENVIRONMENT}...${NC}"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f .env ]; then
        echo -e "${RED}.env file not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Prerequisites check passed${NC}"
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"
    
    # Run unit tests
    docker-compose run --rm app pytest tests/unit -v
    
    # Run integration tests if in staging
    if [ "$ENVIRONMENT" = "staging" ]; then
        docker-compose run --rm app pytest tests/integration -v
    fi
    
    echo -e "${GREEN}Tests passed${NC}"
}

# Function to build images
build_images() {
    echo -e "${YELLOW}Building Docker images...${NC}"
    
    # Build with production optimizations
    docker-compose build --no-cache --pull
    
    echo -e "${GREEN}Images built successfully${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"
    
    # Run migrations
    docker-compose run --rm app python backend/migrations/migrate.py migrate
    
    echo -e "${GREEN}Migrations completed${NC}"
}

# Function to deploy application
deploy_application() {
    echo -e "${YELLOW}Deploying application...${NC}"
    
    # Stop existing containers
    docker-compose down
    
    # Start new containers
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    else
        docker-compose up -d
    fi
    
    # Wait for services to be healthy
    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 10
    
    # Check health
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}Application is healthy${NC}"
    else
        echo -e "${RED}Health check failed${NC}"
        docker-compose logs app
        exit 1
    fi
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${YELLOW}Setting up monitoring...${NC}"
    
    # Create log directories if they don't exist
    mkdir -p logs
    mkdir -p logs/nginx
    mkdir -p logs/app
    
    # Set proper permissions
    chmod 755 logs
    
    echo -e "${GREEN}Monitoring setup completed${NC}"
}

# Function to backup database
backup_database() {
    echo -e "${YELLOW}Creating database backup...${NC}"
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Backup database schema and data
    docker-compose exec -T postgres pg_dump -U postgres my_newsletters > "$BACKUP_DIR/database.sql"
    
    echo -e "${GREEN}Database backed up to $BACKUP_DIR${NC}"
}

# Function to rollback deployment
rollback() {
    echo -e "${RED}Rolling back deployment...${NC}"
    
    # Restore previous version
    docker-compose down
    
    # Restore from backup if available
    if [ -d "backups" ]; then
        LATEST_BACKUP=$(ls -t backups | head -1)
        if [ -n "$LATEST_BACKUP" ]; then
            echo -e "${YELLOW}Restoring from backup: $LATEST_BACKUP${NC}"
            docker-compose up -d postgres
            sleep 5
            docker-compose exec -T postgres psql -U postgres my_newsletters < "backups/$LATEST_BACKUP/database.sql"
        fi
    fi
    
    echo -e "${YELLOW}Rollback completed. Manual intervention may be required.${NC}"
}

# Main deployment flow
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}My Newsletters Voice Assistant Deployment${NC}"
    echo -e "${GREEN}Environment: $ENVIRONMENT${NC}"
    echo -e "${GREEN}Branch: $DEPLOY_BRANCH${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Set trap for rollback on error
    trap rollback ERR
    
    # Run deployment steps
    check_prerequisites
    
    # Git operations
    echo -e "${YELLOW}Pulling latest code...${NC}"
    git fetch origin
    git checkout $DEPLOY_BRANCH
    git pull origin $DEPLOY_BRANCH
    
    # Deployment steps
    run_tests
    backup_database
    build_images
    run_migrations
    deploy_application
    setup_monitoring
    
    # Clear trap
    trap - ERR
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Show status
    docker-compose ps
}

# Run main function
main "$@"