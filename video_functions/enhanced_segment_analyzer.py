#!/usr/bin/env python3
"""
Enhanced Segment Analysis - Gets full user narration for each visual segment
and performs comprehensive AI analysis with proper naming conventions
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Tuple
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class EnhancedSegmentAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def analyze_visual_segments(self, sitemap_path: Path, output_path: Path = None) -> Dict:
        """Analyze visual segments with full user narration context and proper naming"""
        
        with open(sitemap_path) as f:
            sitemap = json.load(f)
        
        # Load complete transcription for user narration
        transcription_path = Path('video_processing/transcription_output/complete_transcription.json')
        with open(transcription_path) as f:
            transcription = json.load(f)
        
        screenshots_dir = Path('video_final_data/screenshots_web_full')
        
        # Get all unique screenshots
        unique_screenshots = set()
        for page in sitemap.get('pages', []):
            for sentence in page.get('visual_segments', page.get('sentences', [])):
                if sentence.get('screenshot'):
                    unique_screenshots.add(sentence['screenshot'])
        
        print(f"Analyzing {len(unique_screenshots)} unique visual segments...")
        
        # Analyze each unique screenshot with full context
        segment_analyses = {}
        
        for i, screenshot in enumerate(unique_screenshots):
            print(f"Analyzing segment {i+1}/{len(unique_screenshots)}: {screenshot}")
            
            # Remove path prefix if present
            screenshot_file = screenshot.replace('screenshots_web_full/', '') if screenshot.startswith('screenshots_web_full/') else screenshot
            screenshot_path = screenshots_dir / screenshot_file
            
            if not screenshot_path.exists():
                print(f"  Warning: Screenshot not found: {screenshot_path}")
                continue
            
            # Get full segment context including complete user narration
            segment_context = self._extract_full_segment_context(screenshot, sitemap, transcription)
            
            # Perform comprehensive segment analysis
            analysis = self._analyze_visual_segment(screenshot_path, segment_context)
            segment_analyses[screenshot] = analysis
        
        # Apply analyses with proper naming conventions
        enhanced_sitemap = self._apply_segment_analyses_with_proper_naming(sitemap, segment_analyses)
        
        # Save enhanced sitemap with proper naming
        if output_path is None:
            output_path = Path('video_final_data/web_full_site_map_enhanced_segments.json')
        with open(output_path, 'w') as f:
            json.dump(enhanced_sitemap, f, indent=2)
        
        print(f"Enhanced segment analysis complete: {output_path}")
        return enhanced_sitemap
    
    def _extract_full_segment_context(self, screenshot: str, sitemap: Dict, transcription: Dict) -> Dict:
        """Extract complete user narration and context for a specific visual segment"""
        
        # Find primary instance and count usage
        primary_page = None
        primary_url = None
        primary_start = None
        primary_end = None
        usage_count = 0
        
        for page in sitemap.get('pages', []):
            for sentence in page.get('visual_segments', page.get('sentences', [])):
                if sentence.get('screenshot') == screenshot:
                    usage_count += 1
                    if primary_page is None:  # First occurrence
                        primary_page = page.get('page_name')
                        primary_url = page.get('relative_url')
                        primary_start = sentence.get('start_timestamp')
                        primary_end = sentence.get('end_timestamp')
        
        if primary_page is None:
            return {
                'full_user_narration': '',
                'usage_count': 0,
                'primary_page': 'Unknown',
                'primary_url': 'unknown'
            }
        
        # Extract full user narration around this timestamp from complete transcription
        full_narration = self._get_full_narration_for_timespan(
            transcription,
            primary_start,
            primary_end
        )
        
        return {
            'full_user_narration': full_narration,
            'usage_count': usage_count,
            'primary_page': primary_page,
            'primary_url': primary_url
        }
    
    def _get_full_narration_for_timespan(self, transcription: Dict, start_time: float, end_time: float) -> str:
        """Extract all user narration within a timespan from complete transcription"""
        
        words = transcription.get('words', [])
        relevant_words = []
        
        # Add some buffer around the timespan to get more context
        buffer_seconds = 5.0
        expanded_start = max(0, start_time - buffer_seconds)
        expanded_end = end_time + buffer_seconds
        
        for word_data in words:
            word_start = word_data.get('start', 0)
            word_end = word_data.get('end', 0)
            
            # Include word if it overlaps with our expanded timespan
            if (word_start <= expanded_end and word_end >= expanded_start):
                relevant_words.append(word_data.get('word', ''))
        
        return ' '.join(relevant_words).strip()
    
    def _analyze_visual_segment(self, screenshot_path: Path, segment_context: Dict) -> Dict:
        """Analyze a visual segment with complete user narration context"""
        try:
            base64_image = self._encode_image(screenshot_path)
            
            # Create comprehensive prompt with full user narration
            primary_page = segment_context['primary_page']
            primary_url = segment_context['primary_url']
            full_narration = segment_context['full_user_narration']
            usage_count = segment_context['usage_count']
            
            prompt = f"""
            VISUAL SEGMENT ANALYSIS
            
            You are analyzing a screenshot from a user demonstration video. The user was explaining the application while navigating through it.
            
            SEGMENT CONTEXT:
            - Primary Page: {primary_page}
            - URL: {primary_url}
            - Used {usage_count} times in video
            - Timestamp: {segment_context.get('timestamp_range', {}).get('start', 'unknown')}s - {segment_context.get('timestamp_range', {}).get('end', 'unknown')}s
            
            COMPLETE USER NARRATION:
            "{full_narration}"
            
            TASK:
            Analyze this screenshot as a distinct visual segment, using the user's complete narration to understand what they were demonstrating.
            
            Provide a JSON response with:
            {{
                "segment_type_classification": "What type of UI state/screen this represents (e.g., 'Calendar Grid View', 'Workout Detail Modal', 'Settings Panel')",
                "comprehensive_segment_description": "Detailed description of this specific visual state, incorporating what the user was explaining",
                "primary_purpose": "What the user was demonstrating or explaining in this segment",
                "key_ui_sections": ["visible UI sections in this state"],
                "actionable_elements": ["specific interactive elements visible"],
                "navigation_elements": ["menus, tabs, breadcrumbs visible"],
                "data_displayed": ["types of information shown"],
                "user_workflow_context": "What step in the user's demonstration this represents",
                "unique_visual_identifiers": ["distinguishing visual features of this segment"],
                "demonstrated_functionality": ["specific features the user was showing"]
            }}
            
            Focus on this SPECIFIC visual state and what the user was explaining about it.
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
                max_tokens=1000
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            try:
                # Clean up response
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                analysis = json.loads(content)
                analysis['segment_context'] = segment_context  # Include full context for reference
            except json.JSONDecodeError:
                # Fallback
                analysis = {
                    "segment_type_classification": "Analysis Failed",
                    "comprehensive_segment_description": content,
                    "primary_purpose": "JSON parsing failed",
                    "key_ui_sections": [],
                    "actionable_elements": [],
                    "navigation_elements": [],
                    "data_displayed": [],
                    "user_workflow_context": "Unknown",
                    "unique_visual_identifiers": [],
                    "demonstrated_functionality": [],
                    "segment_context": segment_context
                }
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing segment {screenshot_path}: {e}")
            return {
                "segment_type_classification": "Error",
                "comprehensive_segment_description": f"Analysis failed: {str(e)}",
                "primary_purpose": "Error",
                "key_ui_sections": [],
                "actionable_elements": [],
                "navigation_elements": [],
                "data_displayed": [],
                "user_workflow_context": "Error",
                "unique_visual_identifiers": [],
                "demonstrated_functionality": [],
                "segment_context": segment_context
            }
    
    def _apply_segment_analyses_with_proper_naming(self, sitemap: Dict, segment_analyses: Dict) -> Dict:
        """Apply segment analyses to sitemap with proper naming conventions"""
        enhanced_sitemap = sitemap.copy()
        
        # Fix naming at processing info level
        processing_info = enhanced_sitemap.get('processing_info', {})
        processing_info['total_visual_segments'] = processing_info.pop('total_sentences', 0)
        processing_info['include_ai_analysis'] = True
        processing_info['ai_analysis_type'] = 'enhanced_segment_level'
        processing_info['enhancement_method'] = 'Full User Narration Context Analysis'
        
        # Fix naming at page level and apply analyses
        for page in enhanced_sitemap.get('pages', []):
            # Rename page-level fields
            if 'start_sentence' in page:
                page['start_segment'] = page.pop('start_sentence')
            if 'end_sentence' in page:
                page['end_segment'] = page.pop('end_sentence')
            if 'sentences' in page:
                page['visual_segments'] = page.pop('sentences')
            
            # Fix naming and apply analyses to visual segments
            for segment in page.get('visual_segments', []):
                # Rename segment-level fields
                if 'sentence_id' in segment:
                    segment['segment_id'] = segment.pop('sentence_id')
                if 'sentence' in segment:
                    segment['user_narration'] = segment.pop('sentence')
                
                # Apply segment analysis with proper naming
                screenshot = segment.get('screenshot')
                if screenshot and screenshot in segment_analyses:
                    segment['segment_analysis'] = segment_analyses[screenshot]
                    
                    # Add the original user text from this specific segment to the analysis
                    original_user_text = segment.get('user_narration', '')
                    segment['segment_analysis']['original_user_text'] = original_user_text
                else:
                    segment['segment_analysis'] = self._create_empty_analysis()
                    segment['segment_analysis']['original_user_text'] = segment.get('user_narration', '')
        
        # Create segment states summary with proper naming
        enhanced_sitemap['unique_segment_states'] = {
            'total_unique_segments': len(segment_analyses),
            'segment_types': []
        }
        
        for screenshot, analysis in segment_analyses.items():
            enhanced_sitemap['unique_segment_states']['segment_types'].append({
                'screenshot': screenshot,
                'segment_type': analysis.get('segment_type_classification', 'Unknown'),
                'primary_purpose': analysis.get('primary_purpose', 'Unknown'),
                'usage_count': analysis.get('segment_context', {}).get('usage_count', 0)
            })
        
        return enhanced_sitemap
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _create_empty_analysis(self) -> Dict:
        """Create empty analysis structure with proper naming"""
        return {
            "segment_type_classification": "Unknown",
            "comprehensive_segment_description": "Analysis unavailable",
            "primary_purpose": "Unknown",
            "key_ui_sections": [],
            "actionable_elements": [],
            "navigation_elements": [],
            "data_displayed": [],
            "user_workflow_context": "Unknown",
            "unique_visual_identifiers": [],
            "demonstrated_functionality": []
        }

def main():
    analyzer = EnhancedSegmentAnalyzer()
    sitemap_path = Path('video_final_data/web_full_site_map.json')
    result = analyzer.analyze_visual_segments(sitemap_path)
    
    print(f"\n=== Enhanced Segment Analysis Results ===")
    print(f"Total unique visual segments analyzed: {result['unique_segment_states']['total_unique_segments']}")
    print(f"Segment types found:")
    for segment_type in result['unique_segment_states']['segment_types'][:10]:  # Show first 10
        print(f"  - {segment_type['segment_type']}: {segment_type['primary_purpose'][:80]}... (used {segment_type['usage_count']} times)")

if __name__ == "__main__":
    main()