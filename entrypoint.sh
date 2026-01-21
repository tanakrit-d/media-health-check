#!/bin/sh
set -e

case "$1" in
  /*|-*|--*)
    exec /app/main.py "$@"
    ;;
esac

echo "Setting up cron job with schedule: $CRON_SCHEDULE"
echo "Scanning directories: $SCAN_DIRECTORIES"
echo "Validator options: $VALIDATOR_OPTIONS"
echo "Output format: $OUTPUT_FORMAT"
echo "Database path: $DB_PATH"

mkdir -p /data/logs

CRON_COMMAND="/app/main.py ${VALIDATOR_OPTIONS} --db-path ${DB_PATH} --output ${OUTPUT_FORMAT} ${SCAN_DIRECTORIES} >> /data/logs/validator-\$(date +\%Y-\%m-\%d).log 2>&1"

echo "${CRON_SCHEDULE} ${CRON_COMMAND}" > /etc/cron.d/video-validator
chmod 0644 /etc/cron.d/video-validator
crontab /etc/cron.d/video-validator

echo "Cron job installed:"
crontab -l

echo ""
echo "Running initial scan..."
/app/main.py ${VALIDATOR_OPTIONS} --db-path ${DB_PATH} --output ${OUTPUT_FORMAT} ${SCAN_DIRECTORIES} \
  | tee /data/logs/validator-$(date +%Y-%m-%d)-startup.log

echo ""
echo "Starting cron daemon..."
exec crond -f
