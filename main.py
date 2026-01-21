#!/usr/bin/env python3
"""
Video file integrity validator.
Features: Parallel scanning, Batch DB commits, Deep Scan mode.
Type-safe and performance optimized.
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from sqlite3 import Connection
from concurrent.futures import ThreadPoolExecutor, as_completed

class VideoValidator:
    VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
    
    def __init__(self, db_path: str, verbose: bool = False, quiet: bool = False, deep_scan: bool = False):
        self.db_path = Path(db_path).expanduser()
        self.verbose = verbose
        self.quiet = quiet
        self.deep_scan = deep_scan
        
        self.conn: Optional[Connection] = None
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with WAL mode for concurrency."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        
        assert self.conn is not None

        self.conn.execute("PRAGMA journal_mode=WAL;") 
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scanned_files (
                filepath TEXT PRIMARY KEY,
                mtime REAL,
                size INTEGER,
                last_scanned TIMESTAMP,
                is_corrupted BOOLEAN,
                scan_type TEXT,
                error_message TEXT
            )
        """)
        self.conn.commit()

    def _log(self, message: str, level: str = "info"):
        if self.quiet:
            return
        if level == "verbose" and not self.verbose:
            return
        sys.stderr.write(f"{message}\n")

    def _find_video_files(self, directories: List[str]) -> List[Path]:
        """Find video files using rglob."""
        video_files = []
        for directory in directories:
            path = Path(directory)
            if not path.is_dir():
                self._log(f"Warning: Skipped non-directory: {directory}")
                continue
            
            for ext in self.VIDEO_EXTENSIONS:
                video_files.extend(path.rglob(f"*{ext}"))
                video_files.extend(path.rglob(f"*{ext.upper()}"))
        
        return sorted(list(set(video_files)))

    def _get_file_info(self, filepath: Path) -> Tuple[float, int]:
        stat = filepath.stat()
        return stat.st_mtime, stat.st_size

    def _needs_scan(self, filepath: Path, force: bool) -> bool:
        """Check if file needs scanning based on DB state."""
        if force:
            return True
        
        assert self.conn is not None
        cursor = self.conn.execute(
            "SELECT mtime, size, is_corrupted, scan_type FROM scanned_files WHERE filepath = ?",
            (str(filepath),)
        )
        row = cursor.fetchone()
        
        if row is None:
            return True
        
        db_mtime, db_size, was_corrupted, last_scan_type = row
        current_mtime, current_size = self._get_file_info(filepath)
        
        # If file changed, rescan
        if current_mtime != db_mtime or current_size != db_size:
            return True
        
        # If it was corrupted, check again
        if was_corrupted:
            return True

        # If we are doing a deep scan but last time was only a quick scan, rescan
        current_scan_type = "deep" if self.deep_scan else "quick"
        if current_scan_type == "deep" and last_scan_type != "deep":
            return True

        return False

    @staticmethod
    def validate_file(filepath: Path, deep_scan: bool) -> Tuple[Path, bool, Optional[str]]:
        """
        Static method to be run in workers.
        Returns: (filepath, is_valid, error_message)
        """
        try:
            if deep_scan:
                # DEEP SCAN: Decodes the stream (slow, accurate)
                # -f null - throws away the output, we just want to see if it errors
                cmd = ['ffmpeg', '-v', 'error', '-i', str(filepath), '-f', 'null', '-']
            else:
                # QUICK SCAN: Checks container headers (fast)
                cmd = ['ffprobe', '-v', 'error', '-show_format', '-show_streams', str(filepath)]

            # Timeout: 30s for quick header check, 5 mins for deep decoding
            result = subprocess.run(cmd, capture_output=True, timeout=300 if deep_scan else 30)
            
            if result.returncode != 0:
                err = result.stderr.decode('utf-8', errors='replace').strip()
                return filepath, False, err or "Process returned non-zero code"
            
            return filepath, True, None

        except subprocess.TimeoutExpired:
            return filepath, False, "Timeout expired"
        except Exception as e:
            return filepath, False, str(e)

    def scan(self, directories: List[str], force: bool = False, prune: bool = False, workers: int = 4) -> Dict:
        start_time = time.time()
        
        if prune:
            self._prune_db()

        self._log("Finding video files...", "verbose")
        all_files = self._find_video_files(directories)
        total_files = len(all_files)
        self._log(f"Found {total_files} video files. Checking status...", "info")

        # 1. Filter files that need scanning
        files_to_scan = []
        skipped_count = 0
        
        for f in all_files:
            if self._needs_scan(f, force):
                files_to_scan.append(f)
            else:
                skipped_count += 1

        self._log(f"Skipping {skipped_count} up-to-date files. Scanning {len(files_to_scan)} files...", "info")

        scanned_count = 0
        corrupted_files = []
        scan_errors = []

        # 2. Parallel Processing
        BATCH_SIZE = 10
        pending_db_updates = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(self.validate_file, f, self.deep_scan): f 
                for f in files_to_scan
            }

            try:
                for i, future in enumerate(as_completed(future_to_file)):
                    filepath, is_valid, error_msg = future.result()
                    
                    scanned_count += 1
                    
                    # Prepare DB update
                    mtime, size = self._get_file_info(filepath)
                    pending_db_updates.append((
                        str(filepath), mtime, size, datetime.now(), 
                        not is_valid, "deep" if self.deep_scan else "quick", error_msg
                    ))

                    # Log failure immediately
                    if not is_valid:
                        self._log(f"✗ CORRUPTED: {filepath} ({error_msg})", "info")
                        corrupted_files.append(str(filepath))
                        if error_msg:
                            scan_errors.append({"filepath": str(filepath), "error": error_msg})
                    elif self.verbose:
                         self._log(f"✓ Valid: {filepath.name}", "verbose")

                    # Batch Commit
                    if len(pending_db_updates) >= BATCH_SIZE:
                        self._batch_update_db(pending_db_updates)
                        pending_db_updates = []
                    
                    # Simple progress indicator
                    if not self.quiet and i % 5 == 0:
                        sys.stderr.write(f"\rProgress: {i+1}/{len(files_to_scan)} scanned")

            except KeyboardInterrupt:
                self._log("\nScan interrupted by user. Saving progress...", "info")
                executor.shutdown(wait=False, cancel_futures=True)
                if pending_db_updates:
                    self._batch_update_db(pending_db_updates)
                raise

            # Commit remaining items
            if pending_db_updates:
                self._batch_update_db(pending_db_updates)

        sys.stderr.write("\n")
        
        return {
            "summary": {
                "total_found": total_files,
                "scanned": scanned_count,
                "skipped": skipped_count,
                "corrupted": len(corrupted_files),
                "duration": round(time.time() - start_time, 2)
            },
            "corrupted_files": corrupted_files,
            "errors": scan_errors
        }

    def _batch_update_db(self, records: List[Tuple]):
        """Efficient batch insert."""
        assert self.conn is not None
        self.conn.executemany("""
            INSERT OR REPLACE INTO scanned_files 
            (filepath, mtime, size, last_scanned, is_corrupted, scan_type, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, records)
        self.conn.commit()

    def _prune_db(self):
        assert self.conn is not None
        cursor = self.conn.execute("SELECT filepath FROM scanned_files")
        to_delete = [row[0] for row in cursor if not Path(row[0]).exists()]
        if to_delete:
            self.conn.executemany("DELETE FROM scanned_files WHERE filepath = ?", [(x,) for x in to_delete])
            self.conn.commit()
            self._log(f"Pruned {len(to_delete)} deleted files from DB", "verbose")

    def close(self):
        if self.conn:
            self.conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Video Validator v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('directories', nargs='+', help='Directories to scan')
    parser.add_argument('--db-path', default='~/.cache/video-validator/scan.db')
    parser.add_argument('--force', action='store_true', help="Ignore history and rescan everything")
    parser.add_argument('--deep', action='store_true', help="Use ffmpeg decoding (slow) instead of ffprobe")
    parser.add_argument('--workers', type=int, default=os.cpu_count() or 4, help="Number of parallel threads")
    parser.add_argument('--prune', action='store_true', help="Remove DB entries for deleted files")
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--json', action='store_true', help="JSON output only")

    args = parser.parse_args()
    validator = VideoValidator(args.db_path, args.verbose, args.quiet, args.deep)

    try:
        results = validator.scan(args.directories, args.force, args.prune, args.workers)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            s = results['summary']
            print("\n=== Scan Complete ===")
            print(f"Duration:  {s['duration']}s")
            print(f"Scanned:   {s['scanned']}")
            print(f"Skipped:   {s['skipped']}")
            print(f"Corrupted: {s['corrupted']}")
            
            if results['corrupted_files']:
                print("\n[!] List of Corrupted Files:")
                for f in results['corrupted_files']:
                    print(f" - {f}")
            else:
                print("\nNo corruption detected.")
            
        sys.exit(1 if results['corrupted_files'] else 0)
        
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        sys.exit(130)
    finally:
        validator.close()

if __name__ == '__main__':
    main()
