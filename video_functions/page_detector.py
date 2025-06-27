#!/usr/bin/env python3
"""
Page Detection Functions
Detect page transitions and organize sentences by page
"""

import json
import re
from pathlib import Path
from typing import List, Dict

class PageDetector:
    def __init__(self):
        self.page_patterns = [
            (r"here we are on the (.*?) page", r"\1"),
            (r"now we're on (.*?),", r"\1"),
            (r"this is the (.*?) page", r"\1"),
            (r"we're on (.*?) and", r"\1"),
            (r"let's go to (.*?)", r"\1"),
            (r"transition to the next page", "transition"),
            (r"green screen", "transition")
        ]
        
        self.page_mappings = {
            "calendar": "Training Calendar",
            "my activities": "My Activities", 
            "activities": "My Activities",
            "today tab": "Today Tab",
            "search workouts": "Search Workouts",
            "workouts": "My Workouts",
            "my workouts": "My Workouts",
            "plans": "Training Plans",
            "training plans": "Training Plans",
            "community plans": "Community Plans",
            "my plans": "My Plans",
            "coach jack": "Coach Jack Plan Builder",
            "plan builder": "Coach Jack Plan Builder",
            "create workout": "Create Workout",
            "profile": "Profile Settings",
            "settings": "Profile Settings"
        }
    
    def detect_pages_from_sentences(self, sentences_with_screenshots: List[Dict], output_dir: Path) -> List[Dict]:
        """
        Detect page transitions and group sentences by page
        
        Args:
            sentences_with_screenshots: List of sentences with screenshot data
            output_dir: Directory to save results
        
        Returns:
            List of page data with grouped sentences
        """
        print(f"Detecting page transitions from {len(sentences_with_screenshots)} sentences...")
        
        pages = []
        current_page = {
            "page_name": "Unknown",
            "start_sentence": 0,
            "end_sentence": None,
            "relative_url": "unknown",
            "sentences": []
        }
        
        for i, sentence_data in enumerate(sentences_with_screenshots):
            sentence_text = sentence_data['sentence'].lower()
            
            # Check for page name patterns
            page_found = False
            for pattern, replacement in self.page_patterns:
                match = re.search(pattern, sentence_text)
                if match:
                    if pattern in ["transition to the next page", "green screen"]:
                        # Mark as transition but don't change page yet
                        sentence_data['is_transition'] = True
                        continue
                    
                    page_name = match.group(1).strip()
                    normalized_page_name = self._normalize_page_name(page_name)
                    
                    # Start new page if we found a different one
                    if normalized_page_name != current_page["page_name"] and current_page["sentences"]:
                        current_page["end_sentence"] = sentence_data['sentence_id'] - 1
                        pages.append(current_page.copy())
                        current_page = {
                            "page_name": normalized_page_name,
                            "start_sentence": sentence_data['sentence_id'],
                            "end_sentence": None,
                            "relative_url": "unknown",
                            "sentences": []
                        }
                    else:
                        current_page["page_name"] = normalized_page_name
                    
                    page_found = True
                    break
            
            current_page["sentences"].append(sentence_data)
        
        # Add the last page
        if current_page["sentences"]:
            current_page["end_sentence"] = sentences_with_screenshots[-1]['sentence_id']
            pages.append(current_page)
        
        print(f"Found {len(pages)} pages:")
        for page in pages:
            sentence_count = len(page['sentences'])
            print(f"  - {page['page_name']}: {sentence_count} sentences (IDs {page['start_sentence']}-{page['end_sentence']})")
        
        # Save page detection results
        output_path = output_dir / "page_detection_results.json"
        with open(output_path, 'w') as f:
            json.dump(pages, f, indent=2)
        
        print(f"Saved page detection results to: {output_path}")
        
        return pages
    
    def _normalize_page_name(self, page_name: str) -> str:
        """Normalize page names to standard format"""
        normalized = page_name.lower().strip()
        return self.page_mappings.get(normalized, page_name.title())
    
    def extract_common_elements(self, pages: List[Dict]) -> Dict:
        """
        Extract common UI elements that appear across multiple pages
        
        Args:
            pages: List of page data
        
        Returns:
            Dictionary of common elements
        """
        # This would analyze multiple screenshots to find recurring elements
        # For now, return a basic structure based on typical trainer day interface
        return {
            "left_navigation": [
                {"item": "Calendar", "description": "Training calendar and workout scheduling"},
                {"item": "Activities", "description": "Completed workout history and analysis"},
                {"item": "Today", "description": "Today's recommended workouts"},
                {"item": "Search", "description": "Search for workouts"},
                {"item": "Workouts", "description": "Workout library and favorites"},
                {"item": "Plans", "description": "Training plan management"}
            ],
            "header_elements": [
                {"item": "User Menu", "description": "User account and settings access"},
                {"item": "Search", "description": "Search functionality across the application"},
                {"item": "Notifications", "description": "System notifications and alerts"},
                {"item": "Export", "description": "Export functionality for various formats"}
            ],
            "recurring_actions": [
                {"action": "Add Workout", "description": "Primary action to add workouts to calendar"},
                {"action": "Export", "description": "Export functionality for various file formats"},
                {"action": "Three Dots Menu", "description": "Context menu for item-specific actions"},
                {"action": "Refresh", "description": "Refresh data from connected services"},
                {"action": "Search", "description": "Search within page content"}
            ]
        }
    
    def validate_page_detection(self, pages: List[Dict]) -> Dict:
        """
        Validate page detection results
        
        Args:
            pages: List of detected pages
        
        Returns:
            Validation statistics
        """
        total_sentences = sum(len(page['sentences']) for page in pages)
        page_names = [page['page_name'] for page in pages]
        unique_pages = len(set(page_names))
        
        # Check for reasonable page distribution
        issues = []
        for page in pages:
            sentence_count = len(page['sentences'])
            if sentence_count < 3:
                issues.append(f"Page '{page['page_name']}' has very few sentences ({sentence_count})")
            elif sentence_count > 100:
                issues.append(f"Page '{page['page_name']}' has many sentences ({sentence_count})")
        
        return {
            "total_pages": len(pages),
            "unique_pages": unique_pages,
            "total_sentences": total_sentences,
            "average_sentences_per_page": total_sentences / len(pages) if pages else 0,
            "page_names": page_names,
            "issues": issues,
            "valid": len(issues) == 0
        }