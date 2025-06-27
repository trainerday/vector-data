#!/usr/bin/env python3
"""
Screenshot Deduplicator - Fast hash-based duplicate removal
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set

class ScreenshotDeduplicator:
    def __init__(self):
        pass
    
    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file for fast duplicate detection"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def deduplicate_screenshots(self, sitemap_path: Path) -> Dict:
        """Fast hash-based deduplication of screenshots"""
        
        with open(sitemap_path) as f:
            sitemap = json.load(f)
        
        screenshots_dir = Path('video_final_data/screenshots_web_full')
        
        print("=== Fast Screenshot Deduplication ===")
        
        # Get referenced files
        referenced_files = set()
        for page in sitemap.get('pages', []):
            for sentence in page.get('visual_segments', page.get('sentences', [])):
                if sentence.get('screenshot'):
                    screenshot = sentence['screenshot']
                    if screenshot.startswith('screenshots_web_full/'):
                        referenced_files.add(screenshot.replace('screenshots_web_full/', ''))
                    else:
                        referenced_files.add(screenshot)
        
        all_files = list(screenshots_dir.glob('*.jpg'))
        unreferenced_files = [f for f in all_files if f.name not in referenced_files]
        
        print(f"Total files: {len(all_files)}")
        print(f"Referenced: {len(referenced_files)}")
        print(f"Unreferenced: {len(unreferenced_files)}")
        
        # Delete unreferenced files
        for file_path in unreferenced_files:
            file_path.unlink()
        
        print(f"Deleted {len(unreferenced_files)} unreferenced files")
        
        # Fast hash-based deduplication of referenced files
        print("\\n=== Hash-based deduplication ===")
        hash_to_file = {}
        duplicates = []
        representatives = {}
        
        for page in sitemap.get('pages', []):
            for sentence in page.get('visual_segments', page.get('sentences', [])):
                if sentence.get('screenshot'):
                    screenshot = sentence['screenshot']
                    if screenshot.startswith('screenshots_web_full/'):
                        filename = screenshot.replace('screenshots_web_full/', '')
                    else:
                        filename = screenshot
                    
                    file_path = screenshots_dir / filename
                    if file_path.exists():
                        file_hash = self.get_file_hash(file_path)
                        
                        if file_hash in hash_to_file:
                            # Duplicate found
                            representative = hash_to_file[file_hash]
                            representatives[screenshot] = representative
                            if file_path not in duplicates:
                                duplicates.append(file_path)
                            print(f"  {screenshot}: DUPLICATE of {representative}")
                        else:
                            # First occurrence
                            hash_to_file[file_hash] = screenshot
                            representatives[screenshot] = screenshot
                            print(f"  {screenshot}: UNIQUE")
        
        # Delete duplicate files
        for file_path in duplicates:
            file_path.unlink()
        
        print(f"\\nDeleted {len(duplicates)} duplicate files")
        
        # Update sitemap references
        updated_count = 0
        for page in sitemap.get('pages', []):
            for sentence in page.get('visual_segments', page.get('sentences', [])):
                if sentence.get('screenshot') and sentence['screenshot'] in representatives:
                    old = sentence['screenshot']
                    new = representatives[old]
                    if old != new:
                        sentence['screenshot'] = new
                        updated_count += 1
        
        # Save updated sitemap
        backup_path = sitemap_path.with_suffix('.backup.json')
        if backup_path.exists():
            backup_path.unlink()  # Remove old backup
        sitemap_path.rename(backup_path)
        
        with open(sitemap_path, 'w') as f:
            json.dump(sitemap, f, indent=2)
        
        # Final count
        final_files = len(list(screenshots_dir.glob('*.jpg')))
        
        results = {
            "original_files": len(all_files),
            "final_files": final_files,
            "total_deleted": len(all_files) - final_files,
            "updated_references": updated_count
        }
        
        print(f"\\n=== Deduplication Results ===")
        print(f"Original files: {results['original_files']}")
        print(f"Final files: {results['final_files']}")
        print(f"Total deleted: {results['total_deleted']}")
        print(f"Updated references: {results['updated_references']}")
        
        return results