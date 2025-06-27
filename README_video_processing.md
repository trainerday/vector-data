# Video Processing Pipeline

A modular video processing pipeline that extracts audio, transcribes it using OpenAI Whisper, cleans the transcript with GPT-4, and maps sentences to timestamps.

## Structure

```
video_functions/
├── __init__.py              # Package initialization
├── audio_splitter.py        # Split large audio files into chunks
├── audio_transcriber.py     # Transcribe audio using OpenAI Whisper
├── transcript_cleaner.py    # Clean transcripts with GPT-4
├── timestamp_mapper.py      # Map sentences to timestamps
├── screenshot_extractor.py  # Extract screenshots from video
├── page_detector.py         # Detect page transitions
├── ai_analyzer.py           # AI analysis with OpenAI Vision
├── sitemap_generator.py     # Generate final sitemap structure
└── video_processor.py       # Main orchestrator

process_video.py             # Main processing script
```

## Features

- **Audio Splitting**: Automatically splits large audio files into chunks under OpenAI's 25MB limit
- **Whisper Transcription**: Uses OpenAI Whisper API with word-level timestamps
- **GPT-4 Cleaning**: Cleans raw transcripts into proper sentences
- **Timestamp Mapping**: Maps cleaned sentences back to original timestamps
- **Screenshot Extraction**: Extracts screenshots from video at sentence timestamps
- **Page Detection**: Automatically detects page transitions and groups content
- **AI Vision Analysis**: Uses OpenAI Vision API to analyze screenshots and enhance descriptions
- **Sitemap Generation**: Creates comprehensive sitemap with UI element detection
- **Validation**: Validates all processing steps and provides detailed statistics

## Usage

### Basic Usage

```bash
# Process with default settings
python process_video.py

# Process specific video and audio files
python process_video.py --video path/to/video.mp4 --audio path/to/audio.mp3

# Custom output directory and chunk size
python process_video.py --output my_output --chunk-size 15

# Skip screenshots or AI analysis for faster processing
python process_video.py --no-screenshots
python process_video.py --no-ai
```

### Check Status

```bash
# Check processing status without running
python process_video.py --status
```

### Command Line Options

- `--video`: Path to video file (default: `video_processing/FullTrainerDayForAI.mp4`)
- `--audio`: Path to audio file (optional, will auto-detect if not provided)
- `--output`: Output directory (default: `video_processing`)
- `--chunk-size`: Audio chunk size in MB (default: 20)
- `--no-screenshots`: Skip screenshot extraction for faster processing
- `--no-ai`: Skip AI vision analysis for faster processing
- `--status`: Check processing status only

## Output Files

The pipeline creates the following files in `{output_dir}/transcription_output/`:

- `complete_transcription.json` - Raw transcription with word-level timestamps
- `cleaned_sentences.json` - List of cleaned sentences
- `sentences_with_timestamps.json` - Sentences mapped to timestamps
- `processing_summary.json` - Complete processing summary and statistics
- `audio_chunk_*.mp3` - Audio chunks (if splitting was needed)
- `transcription_through_chunk_*.json` - Intermediate results

## Environment Setup

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

## Dependencies

```bash
pip install openai python-dotenv pathlib
```

## Example Processing Summary

```json
{
  "audio_file": "video_processing/FullTrainerDayForAI_audio.mp3",
  "file_size_mb": 48.0,
  "chunks_created": 3,
  "transcription": {
    "duration_seconds": 3147.1,
    "duration_minutes": 52.5,
    "total_words": 7129,
    "total_chunks": 3
  },
  "cleaning": {
    "sentences_generated": 215
  },
  "mapping": {
    "sentences_mapped": 215,
    "validation": {
      "valid": true,
      "total_sentences": 215,
      "total_duration": 3147.1
    }
  }
}
```

## Error Handling

- Automatically falls back to simpler sentence splitting if GPT-4 cleaning fails
- Provides detailed error messages for API failures
- Saves intermediate results to prevent data loss
- Validates output consistency

## Customization

Each module can be used independently:

```python
from video_functions.audio_transcriber import AudioTranscriber
from video_functions.transcript_cleaner import TranscriptCleaner

# Use individual components
transcriber = AudioTranscriber()
result = transcriber.transcribe_chunk(audio_path)

cleaner = TranscriptCleaner()
sentences = cleaner.clean_transcript(transcription_data, output_dir)
```