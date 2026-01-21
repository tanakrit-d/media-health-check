#!/bin/sh

DB_PATH=${DB_PATH:-/data/db/scan.db}

[ ! -f "$DB_PATH" ] && exit 1

CORRUPTED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM scanned_files WHERE is_corrupted = 1;")

if [ "$CORRUPTED" -eq 0 ]; then
	exit 0
else
	exit 1
fi
