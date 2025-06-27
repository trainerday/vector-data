#!/usr/bin/env python3
"""
Main Video Processing Script
Complete pipeline for processing video into clean sentences with timestamps
"""

import argparse
import json
from pathlib import Path
from video_functions.video_processor import VideoProcessor

def main():
    parser = argparse.ArgumentParser(description="Process video into clean sentences with timestamps")
    parser.add_argument("--video", help="Path to video file", default="video_processing/web_full.mp4")
    parser.add_argument("--audio", help="Path to audio file (optional)")
    parser.add_argument("--output", help="Output directory", default="video_processing")
    parser.add_argument("--chunk-size", type=int, help="Audio chunk size in MB", default=20)
    parser.add_argument("--no-screenshots", action="store_true", help="Skip screenshot extraction")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis")
    parser.add_argument("--no-dedup", action="store_true", help="Skip screenshot deduplication")
    parser.add_argument("--basic-ai", action="store_true", help="Use basic AI analysis instead of enhanced segment analysis")
    parser.add_argument("--skip-transcription", action="store_true", help="Skip transcription and use existing files")
    parser.add_argument("--status", action="store_true", help="Check processing status only")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = VideoProcessor(args.video, args.output)
    
    if args.status:
        # Just check status
        status = processor.get_processing_status()
        print("=== Processing Status ===")
        print(f"Transcription complete: {status['transcription_complete']}")
        print(f"Cleaning complete: {status['cleaning_complete']}")
        print(f"Mapping complete: {status['mapping_complete']}")
        print(f"Summary available: {status['summary_available']}")
        
        if status.get('last_summary'):
            summary = status['last_summary']
            print(f"\nLast processing results:")
            print(f"  Duration: {summary['transcription']['duration_minutes']:.1f} minutes")
            print(f"  Total words: {summary['transcription']['total_words']:,}")
            print(f"  Clean sentences: {summary['cleaning']['sentences_generated']}")
            print(f"  Mapped sentences: {summary['mapping']['sentences_mapped']}")
        
        return
    
    try:
        # Run complete processing pipeline
        summary = processor.process_complete_video(
            audio_file=args.audio,
            chunk_size_mb=args.chunk_size,
            include_screenshots=not args.no_screenshots,
            include_ai_analysis=not args.no_ai,
            skip_transcription=args.skip_transcription,
            cleanup_duplicate_screenshots=not args.no_dedup,
            use_enhanced_segment_analysis=not args.basic_ai
        )
        
        # Print results summary
        print("\n=== Processing Results ===")
        print(f"Video: {summary['audio_file']}")
        print(f"Duration: {summary['transcription']['duration_minutes']:.1f} minutes")
        print(f"Total words: {summary['transcription']['total_words']:,}")
        print(f"Clean sentences: {summary['cleaning']['sentences_generated']}")
        print(f"Mapped sentences: {summary['mapping']['sentences_mapped']}")
        
        if summary['screenshots']['enabled']:
            screenshot_val = summary['screenshots']['validation']
            if not screenshot_val.get('skipped'):
                print(f"Screenshots extracted: {screenshot_val.get('successful_screenshots', 0)}")
                print(f"Screenshot success rate: {screenshot_val.get('success_rate', 0):.1f}%")
        
        print(f"Pages detected: {summary['page_detection']['pages_detected']}")
        
        if summary['ai_analysis']['enabled']:
            print(f"AI analysis completed: {summary['ai_analysis']['pages_analyzed']} pages")
        
        # Show validation results
        validations = [
            ("Timestamps", summary['mapping']['validation']),
            ("Page detection", summary['page_detection']['validation']),
            ("Sitemap", summary['sitemap']['validation'])
        ]
        
        print(f"\nValidation Results:")
        for name, validation in validations:
            if validation['valid']:
                print(f"  ✅ {name}: passed")
            else:
                print(f"  ⚠️ {name}: {len(validation.get('issues', []))} issues")
        
        print(f"\nKey Output Files:")
        key_files = [
            "final_sitemap", "legacy_sitemap", "sentences_with_screenshots", 
            "ai_enhanced_pages", "statistics"
        ]
        for name in key_files:
            if name in summary['output_files']:
                print(f"  {name}: {summary['output_files'][name]}")
        
        # Show final deliverables location
        video_name = Path(args.video).stem
        print(f"\nFinal Deliverables:")
        print(f"  Main sitemap: video_final_data/{video_name}_site_map.json")
        print(f"  Screenshots: video_final_data/screenshots_{video_name}/")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())