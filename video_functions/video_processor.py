#!/usr/bin/env python3
"""
Main Video Processing Orchestrator
Coordinates all video processing steps
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .audio_splitter import split_audio_file, get_chunk_info
from .audio_transcriber import AudioTranscriber
from .transcript_cleaner import TranscriptCleaner
from .timestamp_mapper import TimestampMapper
from .screenshot_extractor import ScreenshotExtractor
from .page_detector import PageDetector
from .gpt_page_detector import GPTPageDetector
from .ai_analyzer import AIAnalyzer
from .sitemap_generator import SitemapGenerator
from .enhanced_segment_analyzer import EnhancedSegmentAnalyzer
from .screenshot_deduplicator import ScreenshotDeduplicator

class VideoProcessor:
    def __init__(self, video_path: str, output_dir: str = "video_processing"):
        self.video_path = Path(video_path)
        self.output_dir = Path(output_dir)
        self.transcription_dir = self.output_dir / "transcription_output"
        
        # Initialize components
        self.transcriber = AudioTranscriber()
        self.cleaner = TranscriptCleaner()
        self.mapper = TimestampMapper()
        self.screenshot_extractor = ScreenshotExtractor()
        self.page_detector = PageDetector()
        self.gpt_page_detector = GPTPageDetector()
        self.ai_analyzer = AIAnalyzer()
        self.sitemap_generator = SitemapGenerator()
        self.enhanced_segment_analyzer = EnhancedSegmentAnalyzer()
        self.screenshot_deduplicator = ScreenshotDeduplicator()
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.transcription_dir.mkdir(exist_ok=True)
    
    def process_complete_video(
        self, 
        audio_file: Optional[str] = None,
        chunk_size_mb: int = 20,
        include_screenshots: bool = True,
        include_ai_analysis: bool = True,
        skip_transcription: bool = False,
        cleanup_duplicate_screenshots: bool = True,
        use_enhanced_segment_analysis: bool = True
    ) -> Dict:
        """
        Complete video processing pipeline
        
        Args:
            audio_file: Path to audio file (if None, will look for default)
            chunk_size_mb: Size of audio chunks in MB
            include_screenshots: Whether to extract screenshots
            include_ai_analysis: Whether to run AI analysis on screenshots
            skip_transcription: Whether to skip transcription and use existing files
            cleanup_duplicate_screenshots: Whether to delete duplicate screenshots and update references
        
        Returns:
            Processing results summary
        """
        print("=== Video Processing Pipeline ===")
        
        if skip_transcription:
            print("Skipping transcription - using existing files...")
            
            # Load existing files
            transcription_path = self.transcription_dir / "complete_transcription.json"
            cleaned_path = self.transcription_dir / "cleaned_sentences.json"
            mapped_path = self.transcription_dir / "sentences_with_timestamps.json"
            
            if not all(p.exists() for p in [transcription_path, cleaned_path, mapped_path]):
                raise FileNotFoundError("Required transcription files not found. Run without --skip-transcription first.")
            
            # Load transcription data
            with open(transcription_path) as f:
                transcription_data = json.load(f)
            
            # Load cleaned sentences
            with open(cleaned_path) as f:
                cleaned_sentences = json.load(f)
            
            # Load mapped sentences
            with open(mapped_path) as f:
                mapped_sentences = json.load(f)
            
            # Get audio file info
            if audio_file:
                audio_path = Path(audio_file)
            else:
                audio_path = self._find_audio_file()
            
            if not audio_path or not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            chunk_paths = []  # Not needed for skipped transcription
            
            print(f"Using audio file: {audio_path}")
            print(f"Loaded {len(mapped_sentences)} sentences with timestamps")
        else:
            # Step 1: Locate audio file
            if audio_file:
                audio_path = Path(audio_file)
            else:
                audio_path = self._find_audio_file()
            
            if not audio_path or not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            print(f"Using audio file: {audio_path}")
            
            # Step 2: Split audio if needed
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            print(f"Audio file size: {file_size_mb:.1f} MB")
            
            if file_size_mb > 25:  # OpenAI limit
                print("Audio file exceeds OpenAI limit. Splitting into chunks...")
                chunk_paths = split_audio_file(audio_path, self.transcription_dir, chunk_size_mb)
            else:
                print("Audio file within OpenAI limit. Using single file...")
                chunk_paths = [audio_path]
            
            # Step 3: Transcribe audio chunks
            print("\n--- Transcription Phase ---")
            transcription_data = self.transcriber.transcribe_chunks(chunk_paths, self.transcription_dir)
            
            # Step 4: Clean transcript
            print("\n--- Cleaning Phase ---")
            cleaned_sentences = self.cleaner.clean_transcript(transcription_data, self.transcription_dir)
            
            # Step 5: Map timestamps
            print("\n--- Timestamp Mapping Phase ---")
            mapped_sentences = self.mapper.map_sentences_to_timestamps(
                cleaned_sentences, transcription_data, self.transcription_dir
            )
        
        # Step 6: Extract screenshots (if enabled)
        if include_screenshots:
            print("\n--- Screenshot Extraction Phase ---")
            sentences_with_screenshots = self.screenshot_extractor.extract_screenshots_from_sentences(
                self.video_path, mapped_sentences, self.transcription_dir
            )
        else:
            print("\n--- Skipping Screenshot Extraction ---")
            sentences_with_screenshots = mapped_sentences
        
        # Step 7: Detect pages using GPT
        print("\n--- GPT Page Detection Phase ---")
        pages = self.gpt_page_detector.detect_pages_with_gpt(
            sentences_with_screenshots, self.transcription_dir
        )
        
        # Step 8: Extract common elements
        common_elements = self.page_detector.extract_common_elements(pages)
        
        # Step 9: AI analysis (if enabled)
        if include_ai_analysis and include_screenshots:
            if use_enhanced_segment_analysis:
                print("\n--- Enhanced Segment Analysis Phase ---")
                # First generate basic sitemap
                temp_sitemap = self.sitemap_generator.generate_final_sitemap(
                    pages, common_elements, self.transcription_dir,
                    final_output_dir=Path("video_final_data"),
                    video_name=self.video_path.stem,
                    processing_metadata={
                        "video_file": str(self.video_path),
                        "audio_file": str(audio_path),
                        "include_screenshots": include_screenshots,
                        "include_ai_analysis": False  # Will be set to True after enhancement
                    }
                )
                
                # Deduplicate screenshots before AI analysis
                if cleanup_duplicate_screenshots:
                    print("\\n--- Screenshot Deduplication ---")
                    self.screenshot_deduplicator.deduplicate_screenshots(
                        Path("video_final_data") / f"{self.video_path.stem}_site_map.json"
                    )
                
                # Run enhanced segment analysis
                enhanced_sitemap = self.enhanced_segment_analyzer.analyze_visual_segments(
                    Path("video_final_data") / f"{self.video_path.stem}_site_map.json"
                )
                enhanced_pages = enhanced_sitemap.get('pages', [])
            else:
                print("\n--- Basic AI Analysis Phase ---")
                enhanced_pages = self.ai_analyzer.analyze_pages_with_ai(
                    pages, self.transcription_dir, self.transcription_dir, cleanup_duplicate_screenshots
                )
        else:
            print("\n--- Skipping AI Analysis ---")
            enhanced_pages = pages
        
        # Step 10: Generate final sitemap (if not already done by enhanced analysis)
        final_output_dir = Path("video_final_data")
        video_name = self.video_path.stem
        
        if include_ai_analysis and include_screenshots and use_enhanced_segment_analysis:
            print("\n--- Using Enhanced Sitemap ---")
            final_sitemap = enhanced_sitemap
        else:
            print("\n--- Sitemap Generation Phase ---")
            final_sitemap = self.sitemap_generator.generate_final_sitemap(
                enhanced_pages, common_elements, self.transcription_dir,
                final_output_dir=final_output_dir,
                video_name=video_name,
                processing_metadata={
                    "video_file": str(self.video_path),
                    "audio_file": str(audio_path),
                    "include_screenshots": include_screenshots,
                    "include_ai_analysis": include_ai_analysis
                }
            )
        
        # Step 11: Generate legacy format
        legacy_sitemap = self.sitemap_generator.create_legacy_format(
            final_sitemap, self.transcription_dir
        )
        
        # Step 12: Copy final assets to proper location
        self._copy_final_assets(final_output_dir, video_name)
        
        # Step 13: Validate results
        timestamp_validation = self.mapper.validate_timestamps(mapped_sentences)
        page_validation = self.gpt_page_detector.validate_gpt_page_detection(pages) if hasattr(self.gpt_page_detector, 'validate_gpt_page_detection') else {"valid": True, "issues": []}
        sitemap_validation = self.sitemap_generator.validate_sitemap(final_sitemap)
        
        if include_screenshots:
            screenshot_validation = self.screenshot_extractor.validate_screenshots(
                sentences_with_screenshots, self.transcription_dir
            )
        else:
            screenshot_validation = {"skipped": True}
        
        # Create summary
        summary = {
            "audio_file": str(audio_path),
            "file_size_mb": file_size_mb,
            "chunks_created": len(chunk_paths),
            "transcription": {
                "duration_seconds": transcription_data.get('duration', 0),
                "duration_minutes": transcription_data.get('duration', 0) / 60,
                "total_words": transcription_data.get('total_words', 0),
                "total_chunks": transcription_data.get('total_chunks', 0)
            },
            "cleaning": {
                "sentences_generated": len(cleaned_sentences)
            },
            "mapping": {
                "sentences_mapped": len(mapped_sentences),
                "validation": timestamp_validation
            },
            "screenshots": {
                "enabled": include_screenshots,
                "validation": screenshot_validation
            },
            "page_detection": {
                "pages_detected": len(pages),
                "validation": page_validation
            },
            "ai_analysis": {
                "enabled": include_ai_analysis and include_screenshots,
                "pages_analyzed": len(enhanced_pages) if include_ai_analysis else 0
            },
            "sitemap": {
                "validation": sitemap_validation,
                "legacy_format_created": True
            },
            "output_files": {
                "transcription": str(self.transcription_dir / "complete_transcription.json"),
                "cleaned_sentences": str(self.transcription_dir / "cleaned_sentences.json"),
                "mapped_sentences": str(self.transcription_dir / "sentences_with_timestamps.json"),
                "sentences_with_screenshots": str(self.transcription_dir / "sentences_with_screenshots.json"),
                "page_detection": str(self.transcription_dir / "page_detection_results.json"),
                "ai_enhanced_pages": str(self.transcription_dir / "ai_enhanced_pages.json"),
                "final_sitemap": str(self.transcription_dir / "final_sitemap.json"),
                "legacy_sitemap": str(self.transcription_dir / "legacy_sitemap_structure.json"),
                "statistics": str(self.transcription_dir / "sitemap_statistics.json")
            }
        }
        
        # Save summary
        summary_path = self.transcription_dir / "processing_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n🎉 Video processing complete!")
        print(f"Summary saved to: {summary_path}")
        
        return summary
    
    def _find_audio_file(self) -> Optional[Path]:
        """Find the audio file in the video processing directory"""
        # Look for common audio file patterns
        possible_paths = [
            self.output_dir / f"{self.video_path.stem}_audio.mp3",
            self.output_dir / f"{self.video_path.stem}_complete_audio.mp3",
            self.output_dir / f"{self.video_path.stem}.mp3",
            # Legacy naming
            self.output_dir / "FullTrainerDayForAI_audio.mp3"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def get_processing_status(self) -> Dict:
        """Get the current processing status"""
        status = {
            "transcription_complete": (self.transcription_dir / "complete_transcription.json").exists(),
            "cleaning_complete": (self.transcription_dir / "cleaned_sentences.json").exists(),
            "mapping_complete": (self.transcription_dir / "sentences_with_timestamps.json").exists(),
            "summary_available": (self.transcription_dir / "processing_summary.json").exists()
        }
        
        if status["summary_available"]:
            with open(self.transcription_dir / "processing_summary.json") as f:
                status["last_summary"] = json.load(f)
        
        return status
    
    def _copy_final_assets(self, final_output_dir: Path, video_name: str):
        """Copy final assets to the proper location with correct naming"""
        try:
            # Create final output directory
            final_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy screenshots with proper naming
            screenshots_src = self.transcription_dir / "screenshots"
            screenshots_dest = final_output_dir / f"screenshots_{video_name}"
            
            if screenshots_src.exists() and not screenshots_dest.exists():
                shutil.copytree(screenshots_src, screenshots_dest)
                print(f"Screenshots copied to: {screenshots_dest}")
            
            # Update screenshot paths in the final sitemap
            sitemap_path = final_output_dir / f"{video_name}_site_map.json"
            if sitemap_path.exists():
                # Use sed to update paths
                subprocess.run([
                    'sed', '-i', '', 
                    f's/"screenshots\\//"screenshots_{video_name}\\//g',
                    str(sitemap_path)
                ], check=True)
                print(f"Screenshot paths updated in: {sitemap_path}")
                
        except Exception as e:
            print(f"Warning: Could not copy final assets: {e}")