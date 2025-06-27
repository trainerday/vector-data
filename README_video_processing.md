# Enhanced Video Processing Pipeline

Converts video recordings of web application demos into comprehensive sitemaps with enhanced segment analysis, intelligent deduplication, and AI-powered visual understanding.

**📄 Detailed Documentation**: See [AI Test Process - Step 2 Video Processing](memory://ai-testing/ai-test-process-step-2-video-processing) for complete implementation details and big picture context.

## Quick Start

1. **Setup**: Create `.env` file with `OPENAI_API_KEY=your_key`
2. **Add Video**: Copy your video file to `video_processing/` folder as `web_full.mp4`
3. **Process**: Run `python process_video.py` (enhanced analysis + deduplication enabled by default)
4. **Results**: Find final deliverables in `video_final_data/`

## Enhanced Features

- 🎵 **Audio transcription** with OpenAI Whisper (handles large files via chunking)
- 🧠 **GPT-4 sentence cleaning** for readable, structured content
- 📸 **Smart screenshot extraction** at precise sentence midpoints
- ⚡ **Fast hash-based deduplication** (88% screenshot reduction in seconds)
- 🔍 **AI-powered page detection** using natural language understanding
- 🤖 **Enhanced segment analysis** with full user narration context
- 📊 **Comprehensive sitemap generation** with rich visual segment metadata

## Enhanced Command Line Options

```bash
# Enhanced processing (default)
python process_video.py
# → Includes deduplication + enhanced segment analysis

# Custom video file  
python process_video.py --video path/to/video.mp4

# Skip deduplication (for debugging)
python process_video.py --no-dedup

# Use basic AI analysis (legacy mode)
python process_video.py --basic-ai

# Fast processing (skip all AI analysis)
python process_video.py --no-ai

# Reuse existing transcription
python process_video.py --skip-transcription

# Check status only
python process_video.py --status
```

**Enhanced Options:**
- `--video`: Video file path (default: `video_processing/web_full.mp4`)
- `--no-dedup`: Skip screenshot deduplication (keep all 526 screenshots)
- `--basic-ai`: Use legacy basic AI analysis instead of enhanced segment analysis
- `--no-screenshots`: Skip screenshot extraction entirely
- `--no-ai`: Skip all AI vision analysis (fastest processing)
- `--skip-transcription`: Use existing transcription files (for iterative processing)
- `--status`: Check processing status and view summary

## Enhanced Final Output

**📁 `video_final_data/`**
- `web_full_site_map_final.json` - Enhanced sitemap with comprehensive segment analysis
- `web_full_site_map.json.backup` - Backup before deduplication 
- `screenshots_web_full/` - Deduplicated screenshots (30 unique files from original 526)

**Enhanced sitemap includes:**
- **30 unique visual segments** with comprehensive AI analysis (vs 263 redundant sentences)
- **Full user narration context** extracted for each segment with 5-second buffer
- **Rich metadata** per segment: type classification, UI elements, workflow context
- **Proper semantic naming**: `visual_segments` instead of `sentences`
- **Screenshot references** with deduplicated, optimized paths
- **Page detection** and navigation structure 
- **Segment analysis** with demonstrated functionality and actionable elements

**Key improvements:**
- 88% reduction in screenshots (526 → 30 unique)
- Segment-level analysis vs page-level analysis
- Full user narration context for comprehensive understanding
- Fast hash-based deduplication (seconds vs minutes)

## Enhanced Processing Workflow

The improved pipeline follows an optimal processing order:

1. **Audio Processing**: Extract and transcribe with OpenAI Whisper
2. **Text Cleaning**: GPT-4 converts raw transcript to clean sentences  
3. **Timestamp Mapping**: Sequential mapping prevents duplicate timestamps
4. **Screenshot Extraction**: Capture at sentence midpoints (526 screenshots)
5. **Page Detection**: AI-powered natural language page boundary detection
6. **Initial Sitemap**: Generate basic sitemap structure 
7. **⚡ Fast Deduplication**: Hash-based duplicate removal (526 → 30 screenshots)
8. **🤖 Enhanced Analysis**: Full context AI analysis of unique segments only
9. **Final Sitemap**: Enhanced output with comprehensive segment metadata

**Why this order matters:**
- Deduplication before AI analysis saves 88% of API costs
- Enhanced analysis uses full user narration context for better understanding
- Proper semantic naming throughout (visual_segments vs sentences)

## Requirements

```bash
# Install dependencies
pip install openai python-dotenv moviepy opencv-python

# Create .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```