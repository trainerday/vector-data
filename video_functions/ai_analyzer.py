#!/usr/bin/env python3
"""
AI Analysis Functions
Analyze screenshots with OpenAI Vision API to enhance page descriptions
"""

import json
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import os
from dotenv import load_dotenv
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

load_dotenv()

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.similarity_threshold = 0.90  # 90% similarity threshold
    
    def analyze_pages_with_ai(self, pages: List[Dict], base_output_dir: Path, output_dir: Path, cleanup_duplicates: bool = False) -> List[Dict]:
        """
        Analyze pages with OpenAI Vision to enhance descriptions
        
        Args:
            pages: List of page data with sentences and screenshots
            base_output_dir: Base directory containing screenshots
            output_dir: Directory to save enhanced results
            cleanup_duplicates: Whether to delete duplicate screenshots and update references
        
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
            
            # Find unique screenshots for this page
            unique_screenshots = self._find_unique_screenshots(page['sentences'], base_output_dir)
            print(f"  Will analyze {len(unique_screenshots)} unique screenshots out of {len(page['sentences'])} total")
            
            # Create analysis cache for duplicates
            analysis_cache = {}
            
            # Analyze unique screenshots
            for unique_idx, unique_sentence in unique_screenshots:
                print(f"  Analyzing unique screenshot {unique_idx}")
                analysis = self._analyze_screenshot_with_context(unique_sentence, page, base_output_dir)
                analysis_cache[unique_sentence.get('screenshot')] = analysis
            
            # Build enhanced sentences, reusing analysis for similar screenshots
            enhanced_sentences = []
            
            for sent_idx, sentence in enumerate(page['sentences']):
                screenshot_path = sentence.get('screenshot')
                
                # Find the best matching analysis from cache
                analysis = None
                if screenshot_path and screenshot_path in analysis_cache:
                    # Exact match
                    analysis = analysis_cache[screenshot_path]
                else:
                    # Find similar screenshot analysis
                    if screenshot_path:
                        current_img_path = base_output_dir / screenshot_path
                        if current_img_path.exists():
                            best_similarity = 0.0
                            best_analysis = None
                            
                            for cached_screenshot, cached_analysis in analysis_cache.items():
                                cached_img_path = base_output_dir / cached_screenshot
                                if cached_img_path.exists():
                                    similarity = self._calculate_image_similarity(current_img_path, cached_img_path)
                                    if similarity >= self.similarity_threshold and similarity > best_similarity:
                                        best_similarity = similarity
                                        best_analysis = cached_analysis
                            
                            if best_analysis:
                                analysis = best_analysis
                                print(f"  Sentence {sent_idx}: reusing analysis (similarity: {best_similarity:.2%})")
                
                if not analysis:
                    analysis = self._create_empty_analysis()
                
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
        
        # Clean up duplicate screenshots if requested
        if cleanup_duplicates:
            enhanced_pages = self._cleanup_duplicate_screenshots(enhanced_pages, base_output_dir)
        
        # Save enhanced pages
        output_path = output_dir / "ai_enhanced_pages.json"
        with open(output_path, 'w') as f:
            json.dump(enhanced_pages, f, indent=2)
        
        print(f"\n✅ AI analysis complete!")
        print(f"Enhanced pages saved to: {output_path}")
        if cleanup_duplicates:
            print("✅ Duplicate screenshots cleaned up!")
        
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
    
    def _calculate_image_similarity(self, img1_path: Path, img2_path: Path) -> float:
        """Calculate structural similarity between two images"""
        try:
            # Load images
            img1 = cv2.imread(str(img1_path))
            img2 = cv2.imread(str(img2_path))
            
            if img1 is None or img2 is None:
                return 0.0
            
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # Resize to same dimensions if needed
            if gray1.shape != gray2.shape:
                h, w = min(gray1.shape[0], gray2.shape[0]), min(gray1.shape[1], gray2.shape[1])
                gray1 = cv2.resize(gray1, (w, h))
                gray2 = cv2.resize(gray2, (w, h))
            
            # Calculate SSIM
            similarity, _ = ssim(gray1, gray2, full=True)
            return similarity
            
        except Exception as e:
            print(f"Error calculating image similarity: {e}")
            return 0.0
    
    def _find_unique_screenshots(self, sentences: List[Dict], base_output_dir: Path) -> List[Tuple[int, Dict]]:
        """Find unique screenshots by comparing similarity, return list of (index, sentence) tuples"""
        unique_screenshots = []
        processed_images = []
        
        print(f"Analyzing {len(sentences)} screenshots for similarity...")
        
        for idx, sentence in enumerate(sentences):
            if not sentence.get('screenshot'):
                continue
                
            screenshot_path = base_output_dir / sentence['screenshot']
            if not screenshot_path.exists():
                continue
            
            # Compare with all previously processed images
            is_unique = True
            for processed_path, _ in processed_images:
                similarity = self._calculate_image_similarity(screenshot_path, processed_path)
                if similarity >= self.similarity_threshold:
                    print(f"  Screenshot {idx}: {similarity:.2%} similar to existing - SKIPPING")
                    is_unique = False
                    break
            
            if is_unique:
                unique_screenshots.append((idx, sentence))
                processed_images.append((screenshot_path, sentence))
                print(f"  Screenshot {idx}: UNIQUE - will analyze")
        
        print(f"Found {len(unique_screenshots)} unique screenshots out of {len(sentences)} total")
        return unique_screenshots
    
    def _cleanup_duplicate_screenshots(self, enhanced_pages: List[Dict], base_output_dir: Path) -> List[Dict]:
        """Clean up duplicate screenshots and update references"""
        print("Cleaning up duplicate screenshots...")
        
        # Build similarity mapping
        all_screenshots = []
        for page in enhanced_pages:
            for sentence in page['sentences']:
                if sentence.get('screenshot'):
                    all_screenshots.append(sentence['screenshot'])
        
        # Find representatives for each group of similar screenshots
        representatives = {}  # similar_screenshot -> representative_screenshot
        files_to_delete = set()
        
        processed_screenshots = []
        
        for screenshot in all_screenshots:
            screenshot_path = base_output_dir / screenshot
            if not screenshot_path.exists():
                continue
                
            # Find if this screenshot is similar to any processed one
            representative = screenshot
            for processed_screenshot in processed_screenshots:
                processed_path = base_output_dir / processed_screenshot
                if processed_path.exists():
                    similarity = self._calculate_image_similarity(screenshot_path, processed_path)
                    if similarity >= self.similarity_threshold:
                        representative = processed_screenshot
                        files_to_delete.add(screenshot_path)
                        break
            
            representatives[screenshot] = representative
            
            if representative == screenshot:
                processed_screenshots.append(screenshot)
        
        # Delete duplicate files
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")
        
        print(f"Deleted {deleted_count} duplicate screenshot files")
        
        # Update all references in the enhanced pages
        updated_pages = []
        for page in enhanced_pages:
            updated_sentences = []
            for sentence in page['sentences']:
                updated_sentence = sentence.copy()
                if sentence.get('screenshot') and sentence['screenshot'] in representatives:
                    updated_sentence['screenshot'] = representatives[sentence['screenshot']]
                updated_sentences.append(updated_sentence)
            
            updated_page = page.copy()
            updated_page['sentences'] = updated_sentences
            updated_pages.append(updated_page)
        
        print(f"Updated {len(all_screenshots)} screenshot references")
        return updated_pages