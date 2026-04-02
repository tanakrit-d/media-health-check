#!/bin/sh
set -e

SCAN_INTERVAL_HOURS=${SCAN_INTERVAL_HOURS:-24}
SCAN_INTERVAL=$((SCAN_INTERVAL_HOURS * 3600))

echo "Scan interval: ${SCAN_INTERVAL_HOURS} hours (${SCAN_INTERVAL} seconds)"
echo "Scan directories: $SCAN_DIRECTORIES"
echo "Validator options: $VALIDATOR_OPTIONS"
echo "Database path: $DB_PATH"

mkdir -p /data/logs

run_scan() {
	DATE=$(date +%Y-%m)
    LOG_FILE="/data/logs/validator-${DATE}.log"

    echo "Running scan at $(date) → logging to $LOG_FILE"
    echo "=== Scan started at $(date) ===" >> "$LOG_FILE"
    /app/main.py $VALIDATOR_OPTIONS --db-path $DB_PATH --json $SCAN_DIRECTORIES 2>&1 | tee -a "$LOG_FILE"
    echo "=== Scan ended at $(date) ===" >> "$LOG_FILE"
}

run_scan

while true; do
	echo "Sleeping for ${SCAN_INTERVAL_HOURS} hours before next scan..."
    sleep "$SCAN_INTERVAL"
    run_scan
done