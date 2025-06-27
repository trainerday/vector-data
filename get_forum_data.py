#!/usr/bin/env python3
"""
Smart Discourse Forum Data Downloader
Downloads posts, topics, categories, and users from Discourse API with incremental support
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
import argparse
from dotenv import load_dotenv
import sys

load_dotenv()

class DiscourseForumExporter:
    def __init__(self, base_url, api_key=None, api_username=None, output_dir="forum_data"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("DISCOURSE_API_KEY")
        self.api_username = api_username or os.getenv("DISCOURSE_API_USERNAME") or "system"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        if not self.api_key:
            raise ValueError("Discourse API key required. Set DISCOURSE_API_KEY environment variable or pass api_key parameter.")
        
        # Try both authenticated and unauthenticated requests
        self.auth_headers = {
            'Api-Key': self.api_key,
            'Api-Username': self.api_username,
            'Content-Type': 'application/json',
            'User-Agent': 'TrainerDay Forum Scraper 1.0'
        }
        
        self.public_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TrainerDay Forum Scraper 1.0'
        }
        
        # Rate limiting: Discourse typically allows 60 requests per minute
        self.rate_limit_delay = 1  # 1 second between requests to be safe
        
    def make_request(self, endpoint, params=None, use_auth=False):
        """Make a rate-limited request to the Discourse API"""
        url = f"{self.base_url}{endpoint}"
        
        # Add .json extension if not present
        if not url.endswith('.json'):
            url += '.json'
        
        headers = self.auth_headers if use_auth else self.public_headers
        
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"⏱️  Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self.make_request(endpoint, params, use_auth)  # Retry
            elif response.status_code == 403 and not use_auth:
                # Try with authentication if public access fails
                print(f"🔐 Public access failed, trying with authentication...")
                return self.make_request(endpoint, params, use_auth=True)
            else:
                print(f"❌ API Error {response.status_code}: {endpoint}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed for {endpoint}: {e}")
            return None
    
    def get_categories(self):
        """Download all categories"""
        print("📁 Downloading categories...")
        data = self.make_request('/categories')
        
        if data and 'category_list' in data:
            categories = data['category_list']['categories']
            output_file = self.output_dir / "categories.json"
            
            with open(output_file, 'w') as f:
                json.dump(categories, f, indent=2)
            
            print(f"✅ Categories: {len(categories)} saved to {output_file}")
            return categories
        
        return []
    
    def get_latest_topics(self, page=0, per_page=30):
        """Get latest topics with pagination"""
        params = {
            'page': page,
            'per_page': per_page
        }
        
        data = self.make_request('/latest', params)
        
        if data and 'topic_list' in data:
            return data['topic_list']['topics'], data['topic_list'].get('more_topics_url') is not None
        
        return [], False
    
    def get_topic_posts(self, topic_id):
        """Get all posts for a specific topic"""
        data = self.make_request(f'/t/{topic_id}')
        
        if data and 'post_stream' in data:
            return data['post_stream']['posts']
        
        return []
    
    def download_topics_batch(self, start_page=0, max_pages=None):
        """Download topics in batches with full post content"""
        print(f"📝 Downloading topics starting from page {start_page}...")
        
        page = start_page
        total_topics = 0
        total_posts = 0
        
        while True:
            if max_pages and page >= max_pages:
                break
                
            print(f"📄 Processing page {page}...")
            topics, has_more = self.get_latest_topics(page=page)
            
            if not topics:
                print("📄 No more topics found")
                break
            
            for topic in topics:
                topic_id = topic['id']
                topic_slug = topic['slug']
                
                # Get all posts for this topic
                posts = self.get_topic_posts(topic_id)
                
                if posts:
                    # Save topic with its posts
                    topic_data = {
                        'topic': topic,
                        'posts': posts,
                        'downloaded_at': datetime.now().isoformat()
                    }
                    
                    output_file = self.output_dir / f"topic_{topic_id}_{topic_slug[:50]}.json"
                    
                    with open(output_file, 'w') as f:
                        json.dump(topic_data, f, indent=2)
                    
                    total_posts += len(posts)
                    print(f"  ✅ Topic {topic_id}: {len(posts)} posts saved")
                
                total_topics += 1
            
            if not has_more:
                print("📄 Reached end of topics")
                break
                
            page += 1
        
        print(f"📊 Downloaded {total_topics} topics with {total_posts} total posts")
        return total_topics, total_posts
    
    def get_directory_items(self, page=0, period='all', order='likes_received'):
        """Get user directory (public endpoint)"""
        params = {
            'page': page,
            'period': period,
            'order': order
        }
        
        data = self.make_request('/directory_items', params)
        
        if data and 'directory_items' in data:
            return data['directory_items']
        
        return []
    
    def download_users(self, max_pages=5):
        """Download user data from public directory (without sensitive information)"""
        print("👥 Downloading user data from directory...")
        
        all_users = []
        page = 0
        
        while page < max_pages:
            print(f"👤 Processing directory page {page}...")
            users = self.get_directory_items(page)
            
            if not users:
                break
                
            all_users.extend(users)
            page += 1
        
        if all_users:
            output_file = self.output_dir / "users.json"
            
            with open(output_file, 'w') as f:
                json.dump(all_users, f, indent=2)
            
            print(f"✅ Users: {len(all_users)} saved to {output_file}")
        
        return len(all_users)
    
    def find_last_download_date(self):
        """Find the date of the most recent download"""
        files = list(self.output_dir.glob("topic_*.json"))
        
        if not files:
            return None
        
        latest_date = None
        
        for file in files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                if 'downloaded_at' in data:
                    download_date = datetime.fromisoformat(data['downloaded_at']).date()
                    if latest_date is None or download_date > latest_date:
                        latest_date = download_date
                        
            except:
                continue
        
        return latest_date
    
    def full_download(self, max_topic_pages=None, max_user_pages=10):
        """Perform a full download of forum data"""
        print("🚀 Starting full forum download...")
        start_time = time.time()
        
        # Download categories
        categories = self.get_categories()
        
        # Download topics and posts
        total_topics, total_posts = self.download_topics_batch(max_pages=max_topic_pages)
        
        # Download users
        total_users = self.download_users(max_pages=max_user_pages)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"📊 FULL DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"📁 Categories: {len(categories)}")
        print(f"📝 Topics: {total_topics}")
        print(f"💬 Posts: {total_posts}")
        print(f"👥 Users: {total_users}")
        print(f"⏱️  Total time: {elapsed_time/60:.1f} minutes")
        print(f"📁 Data saved to: {self.output_dir.absolute()}")
        
        return {
            'categories': len(categories),
            'topics': total_topics,
            'posts': total_posts,
            'users': total_users
        }
    
    def incremental_download(self, overwrite_last=False):
        """Download only new content since last download (placeholder for future implementation)"""
        print("🔄 Incremental download not yet implemented")
        print("💡 Use full download mode for now")
        
        # For now, just call full download
        return self.full_download()

def main():
    parser = argparse.ArgumentParser(description="Discourse Forum Data Downloader")
    parser.add_argument("--base-url", required=True, help="Discourse forum base URL (e.g., https://your-forum.com)")
    parser.add_argument("--mode", choices=["incremental", "full"], default="full",
                       help="Download mode: incremental (new content only) or full (all content)")
    parser.add_argument("--overwrite-last", action="store_true",
                       help="Overwrite the last download (useful for incomplete data)")
    parser.add_argument("--max-topic-pages", type=int, help="Maximum topic pages to download (default: all)")
    parser.add_argument("--max-user-pages", type=int, default=10, help="Maximum user pages to download")
    parser.add_argument("--api-key", help="Discourse API key (or set DISCOURSE_API_KEY env var)")
    parser.add_argument("--api-username", help="Discourse API username (or set DISCOURSE_API_USERNAME env var)")
    
    args = parser.parse_args()
    
    try:
        # Create exporter
        exporter = DiscourseForumExporter(
            base_url=args.base_url,
            api_key=args.api_key,
            api_username=args.api_username,
            output_dir="forum_data"
        )
        
        if args.mode == "incremental":
            result = exporter.incremental_download(overwrite_last=args.overwrite_last)
        else:
            result = exporter.full_download(
                max_topic_pages=args.max_topic_pages,
                max_user_pages=args.max_user_pages
            )
        
        print(f"\n✅ Download completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()