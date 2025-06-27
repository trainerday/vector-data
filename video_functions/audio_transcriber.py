#!/usr/bin/env python3
"""
Audio Transcription Functions
Transcribe audio chunks using OpenAI Whisper API
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AudioTranscriber:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def transcribe_chunk(self, chunk_path: Path) -> Optional[Dict]:
        """
        Transcribe a single audio chunk
        
        Args:
            chunk_path: Path to audio chunk file
        
        Returns:
            Transcription data dictionary or None if failed
        """
        file_size = chunk_path.stat().st_size / (1024 * 1024)
        print(f"Transcribing {chunk_path.name} ({file_size:.1f} MB)")
        
        try:
            with open(chunk_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            result = transcription.model_dump()
            duration = result.get('duration', 0)
            word_count = len(result.get('words', []))
            
            print(f"  ✅ Duration: {duration:.1f}s ({duration/60:.1f} min), {word_count} words")
            return result
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None
    
    def transcribe_chunks(self, chunk_paths: List[Path], output_dir: Path) -> Dict:
        """
        Transcribe multiple audio chunks and combine results
        
        Args:
            chunk_paths: List of chunk file paths
            output_dir: Directory to save results
        
        Returns:
            Combined transcription data
        """
        output_dir.mkdir(exist_ok=True)
        
        all_words = []
        full_text = ""
        total_duration = 0
        chunk_info = []
        
        for i, chunk_path in enumerate(chunk_paths):
            print(f"\n--- Chunk {i+1}/{len(chunk_paths)} ---")
            
            # Try to transcribe chunk
            chunk_data = self.transcribe_chunk(chunk_path)
            if not chunk_data:
                print(f"Skipping failed chunk {i+1}")
                continue
            
            # Store chunk info
            chunk_start_time = total_duration
            chunk_duration = chunk_data.get('duration', 0)
            chunk_words = chunk_data.get('words', [])
            chunk_text = chunk_data.get('text', '')
            
            chunk_info.append({
                'chunk_number': i + 1,
                'file': chunk_path.name,
                'start_time': chunk_start_time,
                'duration': chunk_duration,
                'words': len(chunk_words)
            })
            
            # Adjust word timestamps for this chunk
            print(f"  Adjusting timestamps by +{total_duration:.1f}s")
            for word in chunk_words:
                word['start'] += total_duration
                word['end'] += total_duration
                all_words.append(word)
            
            # Combine text
            if full_text and not full_text.endswith(' '):
                full_text += " "
            full_text += chunk_text
            
            # Update total duration
            total_duration += chunk_duration
            
            # Save intermediate result
            intermediate_result = {
                'text': full_text.strip(),
                'words': all_words,
                'duration': total_duration,
                'chunks_completed': i + 1
            }
            
            intermediate_path = output_dir / f"transcription_through_chunk_{i+1}.json"
            with open(intermediate_path, 'w') as f:
                json.dump(intermediate_result, f, indent=2)
            
            print(f"  Saved intermediate result")
        
        # Create final combined transcription
        final_result = {
            'text': full_text.strip(),
            'words': all_words,
            'duration': total_duration,
            'total_chunks': len(chunk_paths),
            'total_words': len(all_words),
            'chunk_info': chunk_info
        }
        
        # Save final result
        final_path = output_dir / "complete_transcription.json"
        with open(final_path, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        print(f"\n🎉 Transcription complete!")
        print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        print(f"Total words: {len(all_words)}")
        print(f"Saved to: {final_path}")
        
        return final_result