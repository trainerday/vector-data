#!/usr/bin/env python3
"""
Smart Mixpanel downloader that works backward from recent dates
and adapts based on data availability
"""

import os
import json
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys

class SmartMixpanelExporter:
    def __init__(self, username, password, project_id, output_dir="mixpanel_data"):
        self.project_id = project_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded}"
        self.base_url = "https://data.mixpanel.com/api/2.0/export"
        
    def download_day(self, date):
        """Download data for a single day with error handling"""
        date_str = date.strftime("%Y-%m-%d")
        output_file = self.output_dir / f"mixpanel_{date_str}.json"
        
        # Skip if file already exists and has content
        if output_file.exists() and output_file.stat().st_size > 2:
            print(f"✓ {date_str} (cached)")
            return True, output_file.stat().st_size > 2
        
        params = {
            'from_date': date_str,
            'to_date': date_str,
            'project_id': self.project_id
        }
        
        headers = {
            'accept': 'text/plain',
            'authorization': self.auth_header
        }
        
        # Respect Mixpanel limits: 60 queries/hour, 3 queries/second
        # 60 queries/hour = 1 query per minute to be safe
        time.sleep(60)
        
        try:
            response = requests.get(
                self.base_url, 
                params=params, 
                headers=headers,
                timeout=300
            )
            
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                
                with open(output_file, 'w') as f:
                    json.dump(events, f, indent=2)
                
                has_data = len(events) > 0
                status = "✅" if has_data else "⚪"
                print(f"{status} {date_str}: {len(events)} events")
                return True, has_data
                
            elif response.status_code == 429:
                print(f"⏱️  {date_str}: Rate limited - skipping")
                return False, False
            else:
                print(f"❌ {date_str}: HTTP {response.status_code}")
                return False, False
                
        except Exception as e:
            print(f"❌ {date_str}: {e}")
            return False, False
    
    def smart_download(self, start_date=None, end_date=None, days_back=730):
        """Smart download working backward from end_date"""
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date = datetime.now().date()
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = end_date - timedelta(days=days_back)
        
        print(f"🧠 Smart Mixpanel Download")
        print(f"📅 Target range: {start_date} to {end_date}")
        print(f"🎯 Strategy: Work backward, stop after consecutive empty days\n")
        
        successful = 0
        failed = 0
        consecutive_empty = 0
        max_consecutive_empty = 30  # Stop after 30 consecutive empty days
        
        # Work backward from today
        current_date = end_date
        
        while current_date >= start_date:
            success, has_data = self.download_day(current_date)
            
            if success:
                successful += 1
                if has_data:
                    consecutive_empty = 0  # Reset counter
                else:
                    consecutive_empty += 1
            else:
                failed += 1
                consecutive_empty += 1  # Count failures as empty too
            
            # Stop if too many consecutive empty days
            if consecutive_empty >= max_consecutive_empty:
                print(f"\n🛑 Stopping: {consecutive_empty} consecutive empty days")
                print(f"📊 Likely reached data retention limit around {current_date}")
                break
            
            current_date -= timedelta(days=1)
            
            # Progress update every 50 days
            days_processed = (end_date - current_date).days
            if days_processed % 50 == 0:
                print(f"📈 Progress: {days_processed} days processed, {successful} successful")
        
        return successful, failed, consecutive_empty
    
    def generate_summary(self, successful, failed, consecutive_empty):
        """Generate download summary"""
        total_files = len(list(self.output_dir.glob("mixpanel_*.json")))
        
        # Analyze what we have
        files_with_data = []
        total_events = 0
        
        for json_file in self.output_dir.glob("mixpanel_*.json"):
            if json_file.stat().st_size > 2:
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    if data:  # Non-empty array
                        date_str = json_file.stem.replace("mixpanel_", "")
                        files_with_data.append((date_str, len(data)))
                        total_events += len(data)
                except:
                    continue
        
        print(f"\n{'='*60}")
        print(f"📊 SMART DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Total downloads attempted: {successful + failed}")
        print(f"📁 Files created: {total_files}")
        print(f"💾 Files with data: {len(files_with_data)}")
        print(f"📈 Total events: {total_events:,}")
        
        if files_with_data:
            files_with_data.sort()
            earliest_date = files_with_data[0][0]
            latest_date = files_with_data[-1][0]
            print(f"📅 Data available: {earliest_date} to {latest_date}")
            
            print(f"\n🎯 Top data days:")
            for date, events in sorted(files_with_data, key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {date}: {events:,} events")
        
        if consecutive_empty >= 30:
            print(f"\n💡 Recommendation: Focus downloads on recent periods")
            print(f"   Historical data appears limited beyond certain date")

def main():
    # Configuration
    USERNAME = "export.f0228a.mp-service-account"
    PASSWORD = "tdqaGOIYi8zNirzKTQBP3MbzqkKhItwK"
    PROJECT_ID = "3402283"
    OUTPUT_DIR = "mixpanel_data"
    
    # Create exporter
    exporter = SmartMixpanelExporter(USERNAME, PASSWORD, PROJECT_ID, OUTPUT_DIR)
    
    # Start immediately
    print("🚀 Starting downloads immediately...")
    
    # Smart download (adjust days_back as needed)
    start_time = time.time()
    
    # Download data (works backward from March 31, 2025 to January 1, 2024)
    successful, failed, consecutive_empty = exporter.smart_download(start_date="2024-01-01", end_date="2025-03-31")
    
    elapsed_time = time.time() - start_time
    exporter.generate_summary(successful, failed, consecutive_empty)
    
    print(f"\n⏱️  Total time: {elapsed_time/60:.1f} minutes")
    print(f"📁 Data saved to: {Path(OUTPUT_DIR).absolute()}")

if __name__ == "__main__":
    main()