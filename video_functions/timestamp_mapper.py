#!/usr/bin/env python3
"""
Timestamp Mapping Functions
Map cleaned sentences to timestamps using word-level data
"""

import json
from pathlib import Path
from typing import List, Dict

class TimestampMapper:
    def __init__(self):
        pass
    
    def map_sentences_to_timestamps(
        self, 
        cleaned_sentences: List[str], 
        transcription_data: Dict, 
        output_dir: Path
    ) -> List[Dict]:
        """
        Map cleaned sentences to timestamps using word-level data
        
        Args:
            cleaned_sentences: List of cleaned sentence strings
            transcription_data: Raw transcription with word-level timestamps
            output_dir: Directory to save results
        
        Returns:
            List of sentences with timestamp data
        """
        output_dir.mkdir(exist_ok=True)
        
        word_data = transcription_data.get('words', [])
        if not word_data:
            print("No word-level timestamp data available!")
            return []
        
        print(f"Mapping {len(cleaned_sentences)} sentences using {len(word_data)} word timestamps...")
        
        mapped_sentences = []
        last_word_index = 0  # Track position in word list to ensure sequential processing
        
        for i, sentence in enumerate(cleaned_sentences):
            # Find timestamps for this sentence
            start_time, end_time, last_word_index = self._find_sentence_timestamps(
                sentence, word_data, i, mapped_sentences, last_word_index
            )
            
            # Calculate mid timestamp
            mid_timestamp = start_time + (end_time - start_time) / 2
            
            mapped_sentence = {
                "sentence_id": i,
                "sentence": sentence,
                "start_timestamp": round(start_time, 2),
                "end_timestamp": round(end_time, 2),
                "mid_timestamp": round(mid_timestamp, 2)
            }
            
            mapped_sentences.append(mapped_sentence)
        
        # Save mapped sentences
        mapped_path = output_dir / "sentences_with_timestamps.json"
        with open(mapped_path, 'w') as f:
            json.dump(mapped_sentences, f, indent=2)
        
        print(f"Mapped sentences saved to: {mapped_path}")
        
        if mapped_sentences:
            print(f"Time range: {mapped_sentences[0]['start_timestamp']:.1f}s to {mapped_sentences[-1]['end_timestamp']:.1f}s")
            print(f"Duration covered: {(mapped_sentences[-1]['end_timestamp'] - mapped_sentences[0]['start_timestamp'])/60:.1f} minutes")
        
        return mapped_sentences
    
    def _find_sentence_timestamps(
        self, 
        sentence: str, 
        word_data: List[Dict], 
        sentence_index: int, 
        previous_sentences: List[Dict],
        start_search_index: int = 0
    ) -> tuple:
        """
        Find start and end timestamps for a sentence
        
        Args:
            sentence: The sentence to find timestamps for
            word_data: List of word-level timestamp data
            sentence_index: Index of current sentence
            previous_sentences: Previously processed sentences
            start_search_index: Index to start searching from (ensures sequential processing)
        
        Returns:
            Tuple of (start_time, end_time, next_search_index)
        """
        # Use first 3-5 words to find position in original transcript
        words = sentence.split()[:5]
        search_text = ' '.join(words).lower()
        
        start_time = None
        end_time = None
        next_search_index = start_search_index
        
        # Search for matching words in word data, starting from last position
        for j in range(start_search_index, len(word_data)):
            word_info = word_data[j]
            word_text = word_info.get('word', '').lower().strip('.,!?;:"')
            
            # Check if this could be the start of our sentence
            if word_text and word_text in search_text:
                # Try to match more words to confirm
                match_count = 0
                test_words = sentence.lower().split()
                
                for k in range(j, min(j + 10, len(word_data))):
                    test_word = word_data[k].get('word', '').lower().strip('.,!?;:"')
                    if match_count < len(test_words) and test_word in test_words[match_count:match_count+3]:
                        match_count += 1
                    
                    if match_count >= min(3, len(test_words)):
                        # Found a good match
                        start_time = word_data[j].get('start', 0)
                        
                        # Find end time by looking ahead
                        sentence_words = sentence.split()
                        words_found = 0
                        
                        for m in range(j, min(j + len(sentence_words) + 10, len(word_data))):
                            if words_found >= len(sentence_words) * 0.8:
                                end_time = word_data[m].get('end', start_time + 5)
                                next_search_index = m + 1
                                break
                            words_found += 1
                        
                        if end_time is None:
                            end_time = word_data[min(j + len(sentence_words), len(word_data)-1)].get('end', start_time + 5)
                            next_search_index = j + len(sentence_words)
                        
                        break
                
                if start_time is not None:
                    break
        
        # Fallback timing if not found
        if start_time is None:
            if sentence_index > 0 and previous_sentences:
                start_time = previous_sentences[-1]['end_timestamp'] + 0.5
            else:
                start_time = 0
            
            # Move search index forward to avoid getting stuck
            next_search_index = min(start_search_index + 50, len(word_data))
        
        if end_time is None:
            end_time = start_time + max(3, len(sentence.split()) * 0.4)
        
        return start_time, end_time, next_search_index
    
    def validate_timestamps(self, mapped_sentences: List[Dict]) -> Dict:
        """
        Validate timestamp consistency and provide statistics
        
        Args:
            mapped_sentences: List of mapped sentences
        
        Returns:
            Validation statistics
        """
        if not mapped_sentences:
            return {"valid": False, "error": "No sentences to validate"}
        
        issues = []
        
        # Check for overlapping timestamps
        for i in range(1, len(mapped_sentences)):
            prev_end = mapped_sentences[i-1]['end_timestamp']
            curr_start = mapped_sentences[i]['start_timestamp']
            
            if curr_start < prev_end:
                issues.append(f"Sentence {i}: overlapping timestamps")
        
        # Check for unreasonable gaps
        for i in range(1, len(mapped_sentences)):
            prev_end = mapped_sentences[i-1]['end_timestamp']
            curr_start = mapped_sentences[i]['start_timestamp']
            gap = curr_start - prev_end
            
            if gap > 30:  # More than 30 seconds gap
                issues.append(f"Sentence {i}: large gap ({gap:.1f}s)")
        
        total_duration = (
            mapped_sentences[-1]['end_timestamp'] - 
            mapped_sentences[0]['start_timestamp']
        )
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_sentences": len(mapped_sentences),
            "total_duration": total_duration,
            "average_sentence_length": total_duration / len(mapped_sentences)
        }