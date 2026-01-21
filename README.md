# Media Health Check

A lightweight, containerised video file integrity validator.

This tool scans media libraries for corrupted video files using `ffprobe` (fast) or `ffmpeg` (deep), stores scan results in SQLite, and runs automatically on a cron schedule.  

## Features

- Fast container-level validation using `ffprobe`
- Optional deep scan via full `ffmpeg` decode
- Parallel scanning with configurable worker count
- Persistent SQLite database with incremental rescans
- Automatic pruning of deleted files
- JSON or human-readable output
- Cron-based scheduling inside the container

## Behaviour

- Recursively scans configured directories for video files
- Skips unchanged files using size + mtime tracking
- Validates files in parallel
- Stores results in a SQLite database
- Logs corrupted files and errors
- Runs automatically on a cron schedule

## Usage

Example `docker-compose.yml`

```yaml
version: '3.8'

services:
  media-health-check:
    image: ghcr.io/tanakrit-d/media-health-check:latest
    container_name: media-health-check

    environment:
      CRON_SCHEDULE: "0 7 * * *"
      SCAN_DIRECTORIES: "/data/media/tv /data/media/movies"
      VALIDATOR_OPTIONS: "--verbose --prune"
      DB_PATH: "/data/db/scan.db"
      OUTPUT_FORMAT: "json"

    volumes:
      - /mnt/user/data/media:/data/media:ro
      - /mnt/user/appdata/media-health-check/db:/data/db
      - /mnt/user/appdata/media-health-check/logs:/data/logs

    restart: unless-stopped
```

### Environment Variables

| Variable | Description |
| ----- | ----- |
| CRON_SCHEDULE | Cron schedule (e.g. `0 7 * * *`) |
| SCAN_DIRECTORIES | Space-separated list of directories to scan |
| VALIDATOR_OPTIONS | Additional CLI flags (e.g. `--deep` `--prune`) |
| DB_PATH | Path to SQLite database |
| OUTPUT_FORMAT | json or human-readable output |

> [!NOTE]  
> Paths and options must not contain newlines. Quoting inside cron is limited.

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

- [ ] Docker
- [ ] Media files readable by the container

## License

MIT License
