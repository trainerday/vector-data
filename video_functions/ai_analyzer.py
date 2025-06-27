#!/usr/bin/env python3
"""
AI Analysis Functions
Analyze screenshots with OpenAI Vision API to enhance page descriptions
"""

import json
import base64
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def analyze_pages_with_ai(self, pages: List[Dict], base_output_dir: Path, output_dir: Path) -> List[Dict]:
        """
        Analyze pages with OpenAI Vision to enhance descriptions
        
        Args:
            pages: List of page data with sentences and screenshots
            base_output_dir: Base directory containing screenshots
            output_dir: Directory to save enhanced results
        
        Returns:
            List of enhanced page data
        """
        print(f"Analyzing {len(pages)} pages with OpenAI Vision...")
        
        enhanced_pages = []
        
        for page_idx, page in enumerate(pages):
            print(f"\nProcessing page {page_idx + 1}/{len(pages)}: {page['page_name']}")
            
            # Extract URL from first screenshot if available
            if page['sentences'] and page['sentences'][0].get('screenshot'):
                page['relative_url'] = self._extract_url_from_screenshot(
                    page['sentences'][0], base_output_dir
                )
            
            enhanced_sentences = []
            
            for sent_idx, sentence in enumerate(page['sentences']):
                if sent_idx % 5 == 0:  # Progress update every 5 sentences
                    print(f"  Analyzing sentence {sent_idx + 1}/{len(page['sentences'])}")
                
                # Analyze screenshot with context
                analysis = self._analyze_screenshot_with_context(sentence, page, base_output_dir)
                
                # Create enhanced sentence structure
                enhanced_sentence = {
                    "sentence_id": sentence['sentence_id'],
                    "timestamp": f"{sentence['mid_timestamp']//60:02.0f}:{sentence['mid_timestamp']%60:02.0f}",
                    "user_description": sentence['sentence'],
                    "screenshot": sentence.get('screenshot'),
                    "page_context": {
                        "page_name": page['page_name'],
                        "relative_url": page.get('relative_url', 'unknown')
                    },
                    "ai_analysis": analysis
                }
                
                enhanced_sentences.append(enhanced_sentence)
            
            enhanced_page = {
                "page_name": page['page_name'],
                "relative_url": page.get('relative_url', 'unknown'),
                "sentence_range": [page['start_sentence'], page['end_sentence']],
                "total_sentences": len(enhanced_sentences),
                "sentences": enhanced_sentences
            }
            
            enhanced_pages.append(enhanced_page)
        
        # Save enhanced pages
        output_path = output_dir / "ai_enhanced_pages.json"
        with open(output_path, 'w') as f:
            json.dump(enhanced_pages, f, indent=2)
        
        print(f"\n✅ AI analysis complete!")
        print(f"Enhanced pages saved to: {output_path}")
        
        return enhanced_pages
    
    def _extract_url_from_screenshot(self, sentence: Dict, base_output_dir: Path) -> str:
        """Extract relative URL from screenshot using OpenAI Vision"""
        if not sentence.get('screenshot'):
            return "unknown"
        
        screenshot_path = base_output_dir / sentence['screenshot']
        if not screenshot_path.exists():
            return "unknown"
        
        try:
            base64_image = self._encode_image(screenshot_path)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Look at this screenshot and extract the URL from the browser address bar.
                                Return ONLY the relative path after the domain (e.g., '/calendar', '/activities', '/workouts/123').
                                If no URL is clearly visible in the address bar, return 'unknown'."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50
            )
            
            url = response.choices[0].message.content.strip()
            return url if url and url != 'unknown' else "unknown"
            
        except Exception as e:
            print(f"Error extracting URL from screenshot: {e}")
            return "unknown"
    
    def _analyze_screenshot_with_context(self, sentence: Dict, page: Dict, base_output_dir: Path) -> Dict:
        """Analyze screenshot with full context using OpenAI Vision"""
        if not sentence.get('screenshot'):
            return self._create_empty_analysis()
        
        screenshot_path = base_output_dir / sentence['screenshot']
        if not screenshot_path.exists():
            return self._create_empty_analysis()
        
        try:
            base64_image = self._encode_image(screenshot_path)
            
            prompt = f"""
            Page Context: {page['page_name']} ({page.get('relative_url', 'unknown')})
            User Description: "{sentence['sentence']}"
            Timestamp: {sentence.get('timestamp', 'unknown')}
            
            Analyze this screenshot with the following context:
            1. This is from the {page['page_name']} page
            2. The user described: "{sentence['sentence']}"
            3. The URL path is: {page.get('relative_url', 'unknown')}
            
            Please provide a JSON response with:
            {{
                "comprehensive_page_description": "Detailed description expanding on what the user said",
                "ui_elements_detected": ["element1", "element2", "element3"],
                "possible_user_actions": ["action1", "action2", "action3"],
                "elements_mentioned_by_user": ["specific elements the user referenced"],
                "page_features": ["key features visible on this page"],
                "interaction_context": "How this relates to what the user was demonstrating"
            }}
            
            Focus on actionable UI elements like buttons, menus, forms, navigation items.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            try:
                # Remove markdown code blocks if present
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                analysis = {
                    "comprehensive_page_description": content,
                    "ui_elements_detected": [],
                    "possible_user_actions": [],
                    "elements_mentioned_by_user": [],
                    "page_features": [],
                    "interaction_context": ""
                }
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing screenshot: {e}")
            return self._create_empty_analysis()
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for OpenAI Vision API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _create_empty_analysis(self) -> Dict:
        """Create empty analysis structure for failed cases"""
        return {
            "comprehensive_page_description": "Analysis unavailable",
            "ui_elements_detected": [],
            "possible_user_actions": [],
            "elements_mentioned_by_user": [],
            "page_features": [],
            "interaction_context": ""
        }