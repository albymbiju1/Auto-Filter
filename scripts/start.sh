#!/bin/bash

# CineAI Bot Startup Script
# This script handles starting the bot with proper environment and logging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check required environment variables
required_vars=("BOT_TOKEN" "API_ID" "API_HASH")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables: ${missing_vars[*]}"
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p temp
mkdir -p backups

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
print_status "Python version: $python_version"

# Check if required packages are installed
print_status "Checking dependencies..."

if ! python3 -c "import pyrogram" 2>/dev/null; then
    print_error "Pyrogram not installed. Run: pip install -r requirements.txt"
    exit 1
fi

if ! python3 -c "import motor" 2>/dev/null && [ "$PRIMARY_DB" = "mongo" ]; then
    print_error "Motor not installed. Run: pip install -r requirements.txt"
    exit 1
fi

if ! python3 -c "import sqlalchemy" 2>/dev/null && [ "$PRIMARY_DB" = "postgres" ]; then
    print_error "SQLAlchemy not installed. Run: pip install -r requirements.txt"
    exit 1
fi

# Database health check
print_status "Checking database connectivity..."

if [ "$PRIMARY_DB" = "mongo" ]; then
    if ! python3 -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
async def check():
    try:
        client = AsyncIOMotorClient(os.getenv('MONGO_URI'))
        await client.admin.command('ping')
        print('MongoDB connection successful')
    except Exception as e:
        print(f'MongoDB connection failed: {e}')
        exit(1)
asyncio.run(check())
" 2>/dev/null; then
        print_error "MongoDB connection failed"
        exit 1
    fi

# Start the bot
print_success "All checks passed. Starting CineAI Bot..."

# Set environment for production
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start bot with proper error handling
print_status "Starting in production mode..."
python3 -m app.main 2>&1 | tee -a logs/bot.log