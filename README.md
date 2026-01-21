# Media Health Check

A lightweight, containerised video file integrity validator.

This tool scans media libraries for corrupted video files using `ffprobe` (fast) or `ffmpeg` (deep), stores scan results in SQLite, and runs automatically on a schedule.  

## Features

- Fast container-level validation using `ffprobe`
- Optional deep scan via full `ffmpeg` decode
- Parallel scanning with configurable worker count
- Persistent SQLite database with incremental rescans
- Automatic pruning of deleted files

## Behaviour

- Recursively scans configured directories for video files
- Skips unchanged files using size + mtime tracking
- Validates files in parallel
- Stores results in a SQLite database
- Logs corrupted files and errors
- Triggers healthcheck failure on error

## Usage

Example `docker-compose.yml`

```yaml
---
services:
  media-health-check:
    image: ghcr.io/tanakrit-d/media-health-check:latest
    container_name: media-health-check

    environment:
      SCAN_INTERVAL_HOURS: "24"
      SCAN_DIRECTORIES: "/data/media/tv /data/media/movies"
      VALIDATOR_OPTIONS: "--verbose --prune"
      DB_PATH: "/data/db/scan.db"

    volumes:
      - /mnt/user/data/media:/data/media:ro
      - /mnt/user/appdata/media-health-check/db:/data/db
      - /mnt/user/appdata/media-health-check/logs:/data/logs

    restart: unless-stopped
```

### Environment Variables

| Variable | Description |
| ----- | ----- |
| SCAN_INTERVAL_HOURS | Periodic schedule in hours (e.g. 24) |
| SCAN_DIRECTORIES | Space-separated list of directories to scan |
| VALIDATOR_OPTIONS | Additional CLI flags (e.g. `--deep` `--prune`) |
| DB_PATH | Path to SQLite database |

> [!NOTE]  
> Paths and options must not contain newlines.

## Manual Execution

Run the container with arguments to execute a one-off scan:

```sh
docker run --rm \
  -v /path/to/media:/data/media:ro \
  -v /path/to/db:/data/db \
  ghcr.io/tanakrit-d/media-health-check \
  /data/media --db-path /data/db/scan.db --deep --verbose
```

## Scan Modes

### Quick scan (default)

Uses ffprobe to validate container structure

### Deep scan (--deep)

Fully decodes video streams using ffmpeg (slower, more accurate)

## Exit Codes

- `0` - No corrupted files found
- `1` - Corrupted files detected
- `130` - Interrupted

## Data Persistence

The following paths should be persisted:

- `/data/db` - SQLite scan database
- `/data/logs` - Scan logs
- `/data/media` - Read-only media source

## Requirements

- [x] Docker
- [x] Media files readable by the container

## Example Run

```console
Finding video files...
Found 14511 video files. Checking status...
Skipping 71 up-to-date files. Scanning 14440 files...

Progress: 1/14440 scanned
✓ Valid: 86 - Eighty Six (2021) - S01E05 - 005 - Im With You [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E08 - 008 - Lets Go [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E15 - 016 - Welcome Back [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E11 - 011 - Here We Go [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E07 - 007 - Will You Remember Me [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv

Progress: 6/14440 scanned
✓ Valid: 86 - Eighty Six (2021) - S01E04 - 004 - Real Name [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E01 - 001 - Undertaker [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E10 - 010 - Thank You [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
✓ Valid: 86 - Eighty Six (2021) - S01E09 - 009 - Goodbye [Bluray-1080p v3][10bit][x265][EAC3 2.0][EN+JA]-iVy.mkv
```

```console
Scan interval: 24 hours (86400 seconds)
Scan directories: /data/media/tv /data/media/movies /data/media/anime/series /data/media/anime/movies
Validator options: --verbose --prune
Database path: /data/db/scan.db
Running scan at Wed Jan 21 03:39:53 UTC 2026 → logging to /data/logs/validator-2026-01-21_03-39-53.log
Finding video files...
Found 14511 video files. Checking status...
Skipping 14511 up-to-date files. Scanning 0 files...

{
  "summary": {
    "total_found": 14511,
    "scanned": 0,
    "skipped": 14511,
    "corrupted": 0,
    "duration": 9.77
  },
  "corrupted_files": [],
  "errors": []
}
Sleeping for 86400 seconds before next scan...
```
