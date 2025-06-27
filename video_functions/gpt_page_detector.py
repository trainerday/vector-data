#!/usr/bin/env python3
"""
GPT-based Page Detection
Uses GPT to intelligently detect page transitions from natural language
"""

import json
import os
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

class GPTPageDetector:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI()
    
    def detect_pages_with_gpt(self, sentences_with_timestamps: List[Dict], output_dir: Path) -> List[Dict]:
        """
        Use GPT to detect page transitions from the transcript
        
        Args:
            sentences_with_timestamps: List of sentences with timestamps
            output_dir: Directory to save results
        
        Returns:
            List of page groupings with sentences
        """
        print("Using GPT to detect page transitions...")
        
        # Prepare the transcript for GPT
        transcript_text = self._prepare_transcript_for_gpt(sentences_with_timestamps)
        
        # Get page transitions from GPT
        page_transitions = self._get_page_transitions_from_gpt(transcript_text)
        
        # Apply transitions to create page groupings
        pages = self._apply_transitions_to_sentences(page_transitions, sentences_with_timestamps)
        
        # Save results (save to both GPT-specific and standard filenames)
        gpt_output_path = output_dir / "gpt_page_detection_results.json"
        with open(gpt_output_path, 'w') as f:
            json.dump(pages, f, indent=2)
        
        # Also save to the standard filename that other parts of the pipeline expect
        standard_output_path = output_dir / "page_detection_results.json" 
        with open(standard_output_path, 'w') as f:
            json.dump(pages, f, indent=2)
        
        print(f"Detected {len(pages)} pages using GPT")
        for page in pages:
            print(f"  - {page['page_name']}: {len(page['sentences'])} sentences")
        
        return pages
    
    def _prepare_transcript_for_gpt(self, sentences: List[Dict]) -> str:
        """Prepare transcript text with sentence IDs for GPT analysis"""
        lines = []
        for sent in sentences:
            lines.append(f"[{sent['sentence_id']}] {sent['sentence']}")
        return "\n".join(lines)
    
    def _get_page_transitions_from_gpt(self, transcript: str) -> List[Dict]:
        """Ask GPT to identify page transitions"""
        
        prompt = """Analyze this video transcript where someone is demonstrating a web application's UI. 
Identify every time they transition to a new page or major section of the application.

For each page transition, provide:
1. The sentence ID where the new page starts
2. The name of the page
3. A brief description of what the page is for

Look for phrases like:
- "We are currently on the [page] page"
- "Let's move on to [page]"
- "Transitioning to [page]"
- "Now, let's go to [page]"
- "The next page is [page]"
- Any other natural language indicating a page change

Return the results as a JSON array with this format:
[
  {
    "sentence_id": 0,
    "page_name": "Calendar",
    "description": "Main calendar view for planning workouts"
  },
  ...
]

Transcript:
""" + transcript

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing UI walkthrough videos and identifying page transitions. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure we have an array
            if isinstance(result, dict) and 'pages' in result:
                return result['pages']
            elif isinstance(result, list):
                return result
            else:
                print("Unexpected GPT response format")
                return []
                
        except Exception as e:
            print(f"Error calling GPT: {e}")
            return []
    
    def _apply_transitions_to_sentences(self, transitions: List[Dict], sentences: List[Dict]) -> List[Dict]:
        """Apply the GPT-detected transitions to group sentences into pages"""
        
        pages = []
        current_page = None
        
        # Sort transitions by sentence_id
        transitions.sort(key=lambda x: x['sentence_id'])
        
        # Add a final transition to capture the last page
        transitions.append({
            'sentence_id': len(sentences),
            'page_name': 'END',
            'description': 'End marker'
        })
        
        for i, transition in enumerate(transitions[:-1]):
            start_id = transition['sentence_id']
            end_id = transitions[i + 1]['sentence_id']
            
            # Get sentences for this page
            page_sentences = [s for s in sentences if start_id <= s['sentence_id'] < end_id]
            
            if page_sentences:
                page = {
                    'page_name': transition['page_name'],
                    'description': transition.get('description', ''),
                    'start_sentence': start_id,
                    'end_sentence': end_id - 1,
                    'start_timestamp': page_sentences[0]['start_timestamp'],
                    'end_timestamp': page_sentences[-1]['end_timestamp'],
                    'relative_url': self._generate_url_from_page_name(transition['page_name']),
                    'sentences': page_sentences
                }
                pages.append(page)
        
        return pages
    
    def _generate_url_from_page_name(self, page_name: str) -> str:
        """Generate a URL slug from the page name"""
        # Simple URL generation - could be enhanced
        url_map = {
            'Calendar': '/calendar',
            'My Activities': '/activities',
            'Today': '/today',
            'Search Workouts': '/workouts/search',
            'My Workouts': '/workouts/my',
            'Coach Jack Plan Builder': '/coach-jack',
            'Training Plans': '/plans',
            'My Plans': '/plans/my',
            'Create Workout': '/workouts/create',
            'Profile Settings': '/profile',
            'Home': '/'
        }
        
        return url_map.get(page_name, '/' + page_name.lower().replace(' ', '-'))