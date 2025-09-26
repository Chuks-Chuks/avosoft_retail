#!/bin/bash

# Absolute paths
SCRIPT_DIR="/home/ubuntu/avosoft_retail"
LOG_FILE="$SCRIPT_DIR/cron.log"
ENV_FILE="$SCRIPT_DIR/.env"

# Load environment
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    set +o allexport
    echo "Environment loaded from $ENV_FILE" >> $LOG_FILE
else
    echo "ERROR: .env file not found at $ENV_FILE!" >> $LOG_FILE
    exit 1
fi

# Activate virtual environment
if [ -f "avosoft_env/bin/activate" ]; then
    source avosoft_env/bin/activate
    echo "Virtual environment activated" >> $LOG_FILE
fi

# Run the generator
echo "Running data generator for $(date +%Y-%m-%d)..." >> $LOG_FILE
export PYTHONPATH="$SCRIPT_DIR"
"$SCRIPT_DIR/avosoft_env/bin/python" -m avosoft_engine.cli --date $(date +%Y-%m-%d) >> $LOG_FILE 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "SUCCESS: Data generation completed" >> $LOG_FILE
else
    echo "ERROR: Data generation failed" >> $LOG_FILE
    python -c "
from avosoft_engine.utils.email_notifier import send_gmail_alert
send_gmail_alert('Data Generation Failed', 'Avosoft data generation failed at $(date). Check cron.log for details.')
    "
fi

echo "=== [$(date +"%Y-%m-%d %H:%M:%S")] Completion status: $? ===" >> $LOG_FILE
echo "" >> $LOG_FILE

# Deactivate virtual environment
if [ -f "avosoft_env/bin/activate" ]; then
    deactivate
fi
