#!/usr/bin/env python3
"""
Audio Splitting Functions
Split large audio files into manageable chunks for OpenAI API
"""

from pathlib import Path
from typing import List, Dict

def split_audio_file(audio_path: Path, output_dir: Path, chunk_size_mb: int = 20) -> List[Path]:
    """
    Split audio file into chunks using simple byte splitting
    
    Args:
        audio_path: Path to source audio file
        output_dir: Directory to save chunks
        chunk_size_mb: Size of each chunk in MB
    
    Returns:
        List of chunk file paths
    """
    output_dir.mkdir(exist_ok=True)
    
    file_size = audio_path.stat().st_size
    chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
    
    print(f"Splitting {audio_path.name}: {file_size / (1024 * 1024):.1f} MB")
    print(f"Chunk size: {chunk_size_mb} MB")
    
    chunk_paths = []
    chunk_num = 1
    
    with open(audio_path, 'rb') as src:
        while True:
            chunk_data = src.read(chunk_size)
            if not chunk_data:
                break
            
            chunk_path = output_dir / f"audio_chunk_{chunk_num}.mp3"
            with open(chunk_path, 'wb') as dst:
                dst.write(chunk_data)
            
            actual_size = len(chunk_data) / (1024 * 1024)
            print(f"  Created chunk {chunk_num}: {actual_size:.1f} MB")
            chunk_paths.append(chunk_path)
            chunk_num += 1
    
    print(f"✅ Created {len(chunk_paths)} audio chunks")
    return chunk_paths

def get_chunk_info(chunk_paths: List[Path]) -> List[Dict]:
    """
    Get information about audio chunks
    
    Args:
        chunk_paths: List of chunk file paths
    
    Returns:
        List of chunk information dictionaries
    """
    chunk_info = []
    for i, path in enumerate(chunk_paths):
        size_mb = path.stat().st_size / (1024 * 1024)
        chunk_info.append({
            'chunk_number': i + 1,
            'path': path,
            'size_mb': size_mb,
            'filename': path.name
        })
    
    return chunk_info