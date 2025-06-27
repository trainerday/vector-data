# Video Processing Pipeline

Converts video recordings of web application demos into comprehensive sitemaps with timestamped sentences, screenshots, and AI-powered page detection.

**📄 Detailed Documentation**: See [AI Test Process - Step 2 Video Processing](memory://ai-testing/ai-test-process-step-2-video-processing) for complete implementation details and big picture context.

## Quick Start

1. **Setup**: Create `.env` file with `OPENAI_API_KEY=your_key`
2. **Add Video**: Copy your video file to `video_processing/` folder as `web_full.mp4`
3. **Process**: Run `python process_video.py`
4. **Results**: Find final deliverables in `video_final_data/`

## Main Features

- 🎵 **Audio transcription** with OpenAI Whisper (handles large files via chunking)
- 🧠 **GPT-4 sentence cleaning** for readable, structured content
- 📸 **Screenshot extraction** at precise sentence midpoints
- 🔍 **AI-powered page detection** using natural language understanding
- 📊 **Comprehensive sitemap generation** with UI element analysis

## Command Line Options

```bash
# Basic processing
python process_video.py

# Custom video file  
python process_video.py --video path/to/video.mp4

# Fast processing (skip AI analysis)
python process_video.py --no-ai

# Check status only
python process_video.py --status
```

**Options:**
- `--video`: Video file path (default: `video_processing/web_full.mp4`)
- `--no-screenshots`: Skip screenshot extraction
- `--no-ai`: Skip AI vision analysis (faster)
- `--skip-transcription`: Use existing transcription files
- `--status`: Check processing status only

## Final Output

**📁 `video_final_data/`**
- `web_full_site_map.json` - Complete sitemap with 13 pages, 263 sentences
- `screenshots_web_full/` - All screenshots (526 files)

The sitemap includes:
- Timestamped sentences with user descriptions
- Screenshot references with proper paths  
- Page detection and navigation structure
- Common UI elements and user actions

## Requirements

```bash
# Install dependencies
pip install openai python-dotenv moviepy opencv-python

# Create .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```