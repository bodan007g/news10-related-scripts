#!/usr/bin/env python3
"""
Archive Manager Script
Manages disk space by compressing old content and cleaning up cache files.
"""

import os
import shutil
import zipfile
import json
from datetime import datetime, timedelta
import time

# Configuration
CONTENT_DIR = "content"
CACHE_DIR = "cache"
LOGS_DIR = "logs"
STATUS_FILE = "archive_manager_status.json"
ARCHIVE_AGE_DAYS = 60  # Archive content older than 60 days
CACHE_AGE_DAYS = 7     # Clean cache older than 7 days
LOG_AGE_DAYS = 365     # Keep logs for 1 year

class ArchiveManager:
    def __init__(self):
        self.processed_status = self.load_status()
        self.stats = {
            'archived_months': 0,
            'cleaned_cache_files': 0,
            'cleaned_log_files': 0,
            'bytes_saved': 0,
            'total_archives_created': 0
        }

    def load_status(self):
        """Load processing status from file"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_status(self):
        """Save processing status to file"""
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.processed_status, f, indent=2)

    def get_directory_size(self, directory):
        """Calculate total size of a directory in bytes"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except (OSError, FileNotFoundError):
            pass
        return total

    def format_bytes(self, bytes_count):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

    def archive_old_content(self):
        """Archive content older than ARCHIVE_AGE_DAYS"""
        if not os.path.exists(CONTENT_DIR):
            return

        cutoff_date = datetime.now() - timedelta(days=ARCHIVE_AGE_DAYS)
        
        for month_dir in os.listdir(CONTENT_DIR):
            month_path = os.path.join(CONTENT_DIR, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            # Parse month directory name (YYYY-MM format)
            try:
                month_date = datetime.strptime(month_dir, "%Y-%m")
                if month_date > cutoff_date:
                    continue  # Skip recent months
            except ValueError:
                continue  # Skip invalid directory names
            
            # Check if already archived
            archive_key = f"content:{month_dir}"
            if archive_key in self.processed_status and self.processed_status[archive_key]['status'] == 'archived':
                continue
            
            print(f"Archiving content for {month_dir}...")
            
            # Calculate original size
            original_size = self.get_directory_size(month_path)
            
            # Create archive
            archive_path = os.path.join(CONTENT_DIR, f"{month_dir}_archive.zip")
            try:
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    for root, dirs, files in os.walk(month_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Get relative path for archive
                            arcname = os.path.relpath(file_path, CONTENT_DIR)
                            zipf.write(file_path, arcname)
                
                # Get compressed size
                compressed_size = os.path.getsize(archive_path)
                bytes_saved = original_size - compressed_size
                
                # Remove original directory
                shutil.rmtree(month_path)
                
                # Update statistics
                self.stats['archived_months'] += 1
                self.stats['bytes_saved'] += bytes_saved
                self.stats['total_archives_created'] += 1
                
                # Update status
                self.processed_status[archive_key] = {
                    'status': 'archived',
                    'archive_path': archive_path,
                    'original_size': original_size,
                    'compressed_size': compressed_size,
                    'bytes_saved': bytes_saved,
                    'archived_at': datetime.now().isoformat()
                }
                
                print(f"✓ Archived {month_dir}: {self.format_bytes(original_size)} → {self.format_bytes(compressed_size)} (saved {self.format_bytes(bytes_saved)})")
                
            except Exception as e:
                print(f"Error archiving {month_dir}: {e}")
                # Clean up partial archive
                if os.path.exists(archive_path):
                    os.remove(archive_path)

    def clean_old_cache(self):
        """Remove cache files older than CACHE_AGE_DAYS"""
        if not os.path.exists(CACHE_DIR):
            return

        cutoff_time = time.time() - (CACHE_AGE_DAYS * 24 * 3600)
        cleaned_files = 0
        bytes_cleaned = 0
        
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            
            try:
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime < cutoff_time:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleaned_files += 1
                        bytes_cleaned += file_size
            except (OSError, FileNotFoundError):
                pass
        
        self.stats['cleaned_cache_files'] = cleaned_files
        self.stats['bytes_saved'] += bytes_cleaned
        
        if cleaned_files > 0:
            print(f"✓ Cleaned {cleaned_files} old cache files ({self.format_bytes(bytes_cleaned)})")

    def clean_old_logs(self):
        """Remove log files older than LOG_AGE_DAYS"""
        if not os.path.exists(LOGS_DIR):
            return

        cutoff_date = datetime.now() - timedelta(days=LOG_AGE_DAYS)
        cleaned_files = 0
        bytes_cleaned = 0
        
        for month_dir in os.listdir(LOGS_DIR):
            month_path = os.path.join(LOGS_DIR, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            # Parse month directory name
            try:
                month_date = datetime.strptime(month_dir, "%Y-%m")
                if month_date > cutoff_date:
                    continue  # Keep recent logs
            except ValueError:
                continue
            
            # Remove old log directory
            try:
                dir_size = self.get_directory_size(month_path)
                shutil.rmtree(month_path)
                cleaned_files += 1
                bytes_cleaned += dir_size
                print(f"✓ Removed old logs: {month_dir} ({self.format_bytes(dir_size)})")
            except (OSError, FileNotFoundError):
                pass
        
        self.stats['cleaned_log_files'] = cleaned_files
        self.stats['bytes_saved'] += bytes_cleaned

    def clean_status_files(self):
        """Remove old processing status entries"""
        # Keep only the most recent status entries (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for key in list(self.processed_status.keys()):
            try:
                if 'archived_at' in self.processed_status[key]:
                    archived_date = datetime.fromisoformat(self.processed_status[key]['archived_at'])
                    if archived_date < cutoff_date:
                        del self.processed_status[key]
                elif 'processed_at' in self.processed_status[key]:
                    processed_date = datetime.fromisoformat(self.processed_status[key]['processed_at'])
                    if processed_date < cutoff_date:
                        del self.processed_status[key]
            except (ValueError, KeyError):
                pass

    def generate_disk_usage_report(self):
        """Generate a report of current disk usage"""
        report = []
        report.append("=== Disk Usage Report ===")
        
        # Content directory
        if os.path.exists(CONTENT_DIR):
            content_size = self.get_directory_size(CONTENT_DIR)
            report.append(f"Content directory: {self.format_bytes(content_size)}")
            
            # List archives
            archives = [f for f in os.listdir(CONTENT_DIR) if f.endswith('_archive.zip')]
            if archives:
                total_archive_size = sum(os.path.getsize(os.path.join(CONTENT_DIR, f)) for f in archives)
                report.append(f"Archives ({len(archives)} files): {self.format_bytes(total_archive_size)}")
        
        # Cache directory
        if os.path.exists(CACHE_DIR):
            cache_size = self.get_directory_size(CACHE_DIR)
            cache_files = len(os.listdir(CACHE_DIR))
            report.append(f"Cache directory ({cache_files} files): {self.format_bytes(cache_size)}")
        
        # Logs directory
        if os.path.exists(LOGS_DIR):
            logs_size = self.get_directory_size(LOGS_DIR)
            report.append(f"Logs directory: {self.format_bytes(logs_size)}")
        
        return "\n".join(report)

    def run(self):
        """Main processing function"""
        start_time = time.time()
        print(f"Archive Manager started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate initial disk usage report
        print("\n" + self.generate_disk_usage_report())
        print()
        
        # Perform cleanup tasks
        self.archive_old_content()
        self.clean_old_cache()
        self.clean_old_logs()
        self.clean_status_files()
        
        # Save updated status
        self.save_status()
        
        elapsed = time.time() - start_time
        
        print(f"\n=== Archive Manager Summary ===")
        print(f"Archived months: {self.stats['archived_months']}")
        print(f"Archives created: {self.stats['total_archives_created']}")
        print(f"Cache files cleaned: {self.stats['cleaned_cache_files']}")
        print(f"Log directories cleaned: {self.stats['cleaned_log_files']}")
        print(f"Total space saved: {self.format_bytes(self.stats['bytes_saved'])}")
        print(f"Total time: {elapsed:.2f} seconds")
        
        # Generate final disk usage report
        print("\n" + self.generate_disk_usage_report())
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "archive_manager_summary.log")
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Archived: {self.stats['archived_months']} | "
            f"Cache cleaned: {self.stats['cleaned_cache_files']} | "
            f"Logs cleaned: {self.stats['cleaned_log_files']} | "
            f"Space saved: {self.format_bytes(self.stats['bytes_saved'])} | "
            f"Time: {elapsed_time:.2f}s\n"
        )
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    manager = ArchiveManager()
    manager.run()