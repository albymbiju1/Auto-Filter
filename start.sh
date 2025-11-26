#!/bin/bash

echo "====================================="
echo "Starting CineAI Bot"
echo "====================================="

# Test environment variables
echo "Testing environment variables..."
python test_env.py

if [ $? -ne 0 ]; then
    echo "Environment variable check failed!"
    echo "Printing available env vars (first 10 chars only for security):"
    env | grep -E "BOT_|API_|MONGO_|ADMIN_" | sed 's/=.*/=.../'
    exit 1
fi

echo "Environment variables OK. Starting bot..."
python -m app.main
