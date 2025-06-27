#!/usr/bin/env python3
"""
Screenshot Extraction Functions
Extract screenshots from video at specific timestamps
"""

import json
from pathlib import Path
from typing import List, Dict
from moviepy.video.io.VideoFileClip import VideoFileClip

class ScreenshotExtractor:
    def __init__(self):
        pass
    
    def extract_screenshots_from_sentences(
        self, 
        video_path: Path, 
        sentences_with_timestamps: List[Dict], 
        output_dir: Path
    ) -> List[Dict]:
        """
        Extract screenshots from video at sentence timestamps
        
        Args:
            video_path: Path to source video file
            sentences_with_timestamps: List of sentences with timestamp data
            output_dir: Directory to save screenshots
        
        Returns:
            List of sentences with screenshot paths added
        """
        screenshots_dir = output_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        
        print(f"Extracting {len(sentences_with_timestamps)} screenshots from video...")
        print(f"Video: {video_path}")
        print(f"Output: {screenshots_dir}")
        
        # Load video
        video = VideoFileClip(str(video_path))
        video_duration = video.duration
        
        print(f"Video duration: {video_duration/60:.1f} minutes")
        
        enhanced_sentences = []
        
        for i, sentence_data in enumerate(sentences_with_timestamps):
            sentence_id = sentence_data['sentence_id']
            mid_timestamp = sentence_data['mid_timestamp']
            
            # Ensure timestamp is within video bounds
            screenshot_time = min(mid_timestamp, video_duration - 1)
            
            # Generate screenshot filename
            screenshot_filename = f"sentence_{sentence_id:03d}_mid_{screenshot_time:.1f}s.jpg"
            screenshot_path = screenshots_dir / screenshot_filename
            
            try:
                # Extract frame at timestamp
                frame = video.get_frame(screenshot_time)
                
                # Save frame as image
                from PIL import Image
                img = Image.fromarray(frame.astype('uint8'))
                img.save(screenshot_path, 'JPEG', quality=85)
                
                # Add screenshot info to sentence data
                enhanced_sentence = sentence_data.copy()
                enhanced_sentence['screenshot'] = f"screenshots/{screenshot_filename}"
                enhanced_sentence['screenshot_timestamp'] = screenshot_time
                
                enhanced_sentences.append(enhanced_sentence)
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i + 1}/{len(sentences_with_timestamps)} screenshots")
                
            except Exception as e:
                print(f"  Error extracting screenshot for sentence {sentence_id}: {e}")
                # Add sentence without screenshot
                enhanced_sentence = sentence_data.copy()
                enhanced_sentence['screenshot'] = None
                enhanced_sentence['screenshot_timestamp'] = screenshot_time
                enhanced_sentences.append(enhanced_sentence)
        
        video.close()
        
        print(f"✅ Screenshot extraction complete!")
        print(f"Extracted {len([s for s in enhanced_sentences if s.get('screenshot')])} screenshots")
        
        # Save enhanced sentences with screenshots
        output_path = output_dir / "sentences_with_screenshots.json"
        with open(output_path, 'w') as f:
            json.dump(enhanced_sentences, f, indent=2)
        
        print(f"Saved enhanced sentences to: {output_path}")
        
        return enhanced_sentences
    
    def validate_screenshots(self, sentences_with_screenshots: List[Dict], output_dir: Path) -> Dict:
        """
        Validate screenshot extraction results
        
        Args:
            sentences_with_screenshots: List of sentences with screenshot data
            output_dir: Directory containing screenshots
        
        Returns:
            Validation statistics
        """
        screenshots_dir = output_dir / "screenshots"
        
        total_sentences = len(sentences_with_screenshots)
        successful_screenshots = 0
        missing_files = []
        
        for sentence in sentences_with_screenshots:
            if sentence.get('screenshot'):
                screenshot_path = output_dir / sentence['screenshot']
                if screenshot_path.exists():
                    successful_screenshots += 1
                else:
                    missing_files.append(sentence['screenshot'])
        
        return {
            "total_sentences": total_sentences,
            "successful_screenshots": successful_screenshots,
            "success_rate": successful_screenshots / total_sentences * 100,
            "missing_files": missing_files,
            "screenshots_directory": str(screenshots_dir)
        }