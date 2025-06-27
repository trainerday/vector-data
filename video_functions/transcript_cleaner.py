#!/usr/bin/env python3
"""
Transcript Cleaning Functions
Clean transcripts into proper sentences using GPT-4
"""

import json
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class TranscriptCleaner:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def clean_transcript(self, transcription_data: Dict, output_dir: Path) -> List[str]:
        """
        Clean transcript into clear sentences using GPT-4
        
        Args:
            transcription_data: Raw transcription data
            output_dir: Directory to save results
        
        Returns:
            List of cleaned sentences
        """
        output_dir.mkdir(exist_ok=True)
        
        full_text = transcription_data['text']
        print(f"Cleaning transcript with GPT-4...")
        print(f"Text length: {len(full_text):,} characters")
        
        # Split text into chunks for GPT processing
        max_chunk_size = 6000
        text_chunks = self._split_text_into_chunks(full_text, max_chunk_size)
        
        print(f"Processing {len(text_chunks)} text chunks...")
        
        all_cleaned_sentences = []
        
        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")
            
            try:
                sentences = self._clean_text_chunk(chunk, len(all_cleaned_sentences))
                all_cleaned_sentences.extend(sentences)
                print(f"  Added {len(sentences)} sentences")
                
            except Exception as e:
                print(f"Error cleaning chunk {i+1}: {e}")
                # Fallback: split by periods
                fallback_sentences = self._fallback_sentence_split(chunk)
                all_cleaned_sentences.extend(fallback_sentences)
        
        print(f"Generated {len(all_cleaned_sentences)} cleaned sentences")
        
        # Save cleaned sentences
        cleaned_path = output_dir / "cleaned_sentences.json"
        with open(cleaned_path, 'w') as f:
            json.dump(all_cleaned_sentences, f, indent=2)
        
        print(f"Saved cleaned sentences to: {cleaned_path}")
        return all_cleaned_sentences
    
    def _split_text_into_chunks(self, text: str, max_chunk_size: int) -> List[str]:
        """Split text into chunks while preserving sentence boundaries"""
        if len(text) <= max_chunk_size:
            return [text]
        
        text_chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) > max_chunk_size:
                if current_chunk:
                    text_chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
                else:
                    # Single sentence too long, force split
                    text_chunks.append(sentence[:max_chunk_size])
                    current_chunk = sentence[max_chunk_size:] + ". "
            else:
                current_chunk += sentence + ". "
        
        if current_chunk:
            text_chunks.append(current_chunk.strip())
        
        return text_chunks
    
    def _clean_text_chunk(self, chunk: str, sentence_offset: int) -> List[str]:
        """Clean a single text chunk using GPT-4"""
        prompt = f"""
        Clean up this video transcript and convert it into clear, numbered sentences.
        
        Original transcript:
        {chunk}
        
        Please:
        1. Remove filler words (um, uh, you know, etc.)
        2. Fix grammar and sentence structure
        3. Keep technical terms accurate (like "FTP", "TrainingPeaks", "Strava", etc.)
        4. Break into logical, complete sentences
        5. Number each sentence starting from {sentence_offset + 1}
        6. Keep the meaning and intent intact
        
        Return ONLY the numbered sentences, one per line:
        {sentence_offset + 1}. First clean sentence here.
        {sentence_offset + 2}. Second clean sentence here.
        etc.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.1
        )
        
        cleaned_text = response.choices[0].message.content.strip()
        
        # Parse numbered sentences
        sentences = []
        lines = cleaned_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or '. ' in line):
                # Extract sentence text (remove number prefix)
                if '. ' in line:
                    sentence_text = line.split('. ', 1)[1]
                    sentences.append(sentence_text)
        
        return sentences
    
    def _fallback_sentence_split(self, chunk: str) -> List[str]:
        """Fallback method to split text when GPT fails"""
        sentences = []
        fallback_sentences = chunk.split('. ')
        for sentence in fallback_sentences:
            if len(sentence.strip()) > 10:
                sentences.append(sentence.strip() + '.')
        return sentences