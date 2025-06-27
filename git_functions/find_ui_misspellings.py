#!/usr/bin/env python3
"""
Comprehensive search for misspellings in user-facing text
Distinguishes between code and actual user-visible strings
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

class UISpellChecker:
    def __init__(self):
        self.misspellings = {
            # Common misspellings -> correct spelling
            'seperate': 'separate',
            'recieve': 'receive', 
            'occured': 'occurred',
            'definately': 'definitely',
            'accessable': 'accessible',
            'begining': 'beginning',
            'calender': 'calendar',
            'excercise': 'exercise',
            'sucessful': 'successful',
            'sucessfull': 'successful',
            'neccessary': 'necessary',
            'recomend': 'recommend',
            'accomodate': 'accommodate',
            'maintainance': 'maintenance',
            'existance': 'existence',
            'thier': 'their',
            'wich': 'which',
            'recieved': 'received',
            'untill': 'until',
            'tommorrow': 'tomorrow',
            'completly': 'completely',
            'availble': 'available',
            'performace': 'performance',
            'appearence': 'appearance',
            'independant': 'independent',
            'alot': 'a lot',
            'teh': 'the',
            'prefered': 'preferred',
            'optmized': 'optimized',
            'membreship': 'membership',
            'activites': 'activities',
            'priviledge': 'privilege',
            'embarass': 'embarrass',
            'persistant': 'persistent',
            'preffered': 'preferred',
            'lenght': 'length',
            'heighth': 'height',
            'widht': 'width',
            'similiar': 'similar',
            'definately': 'definitely',
            'occassion': 'occasion',
            'accomodate': 'accommodate',
            'arguement': 'argument',
            'concious': 'conscious',
            'gaurantee': 'guarantee',
            'harrass': 'harass',
            'liason': 'liaison',
            'minature': 'miniature',
            'noticable': 'noticeable',
            'occurance': 'occurrence',
            'referal': 'referral',
            'transfered': 'transferred',
            'goverment': 'government',
            'enviroment': 'environment'
        }
        
        self.grammar_patterns = [
            (r'\bmust be more (\d+)\b', r'must be more than \1'),
            (r'\bmust be at least 1 ([a-z]+) record', r'must have at least one \1 record'),
            (r'\bappear in your ([a-z]+) units', r'appears in your \1 units'),
            (r'\bdata.*appear\b', 'data should use "appears" (singular)'),
        ]
        
        self.brand_names = {
            'strava': 'Strava',
            'garmin': 'Garmin', 
            'trainingpeaks': 'TrainingPeaks',
            'zwift': 'Zwift',
            'wahoo': 'Wahoo'
        }
        
        self.found_errors = []

    def check_json_file(self, file_path: Path):
        """Check JSON translation files for user-facing text errors"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._check_json_values(data, file_path, [])
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    def _check_json_values(self, obj, file_path: Path, key_path: List[str]):
        """Recursively check JSON values (not keys) for misspellings"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                self._check_json_values(value, file_path, key_path + [key])
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._check_json_values(item, file_path, key_path + [str(i)])
        elif isinstance(obj, str):
            # This is actual user-facing text
            self._check_string(obj, file_path, '.'.join(key_path))

    def _check_string(self, text: str, file_path: Path, context: str):
        """Check a string for misspellings and grammar issues"""
        # Check for misspellings
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        for word in words:
            if word in self.misspellings:
                self.found_errors.append({
                    'type': 'misspelling',
                    'file': str(file_path),
                    'context': context,
                    'text': text,
                    'error': word,
                    'correction': self.misspellings[word],
                    'full_text': text
                })
        
        # Check for brand name capitalization in user text
        for incorrect, correct in self.brand_names.items():
            if incorrect in text.lower() and correct not in text:
                # Make sure it's not part of a URL or code
                if not re.search(r'https?://|\.com|\.js|\.ts', text):
                    self.found_errors.append({
                        'type': 'brand_capitalization',
                        'file': str(file_path),
                        'context': context,
                        'text': text,
                        'error': incorrect,
                        'correction': correct,
                        'full_text': text
                    })
        
        # Check grammar patterns
        for pattern, suggestion in self.grammar_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.found_errors.append({
                    'type': 'grammar',
                    'file': str(file_path),
                    'context': context,
                    'text': text,
                    'error': 'Grammar issue',
                    'correction': suggestion,
                    'full_text': text
                })

    def check_vue_file(self, file_path: Path):
        """Check Vue files for user-facing text in templates"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract template section
            template_match = re.search(r'<template[^>]*>(.*?)</template>', content, re.DOTALL)
            if template_match:
                template_content = template_match.group(1)
                
                # Find text content in templates (between > and < but not in attributes)
                # This is a simplified extraction - could be more sophisticated
                text_matches = re.findall(r'>([^<]+)<', template_content)
                for i, text in enumerate(text_matches):
                    text = text.strip()
                    if text and not text.startswith('{{') and len(text) > 2:
                        self._check_string(text, file_path, f'template_text_{i}')
                
                # Find placeholder and alt text attributes
                attr_matches = re.findall(r'(?:placeholder|alt|title)=["\']([^"\']+)["\']', template_content)
                for i, text in enumerate(attr_matches):
                    self._check_string(text, file_path, f'attribute_{i}')
                    
        except Exception as e:
            print(f"Error reading Vue file {file_path}: {e}")

    def check_ts_js_file(self, file_path: Path):
        """Check TypeScript/JavaScript files for user-facing strings"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find strings that look like user messages
            # Look for strings in quotes that contain common user-facing words
            user_indicators = ['error', 'message', 'text', 'alert', 'confirm', 'warning', 'success']
            
            # Find string literals
            string_matches = re.findall(r'["\']([^"\']{10,})["\']', content)
            for i, text in enumerate(string_matches):
                # Check if this looks like user-facing text
                if any(indicator in text.lower() for indicator in user_indicators):
                    self._check_string(text, file_path, f'string_literal_{i}')
                elif re.search(r'\b(must|should|please|cannot|error|failed|success)\b', text.lower()):
                    self._check_string(text, file_path, f'user_message_{i}')
                    
        except Exception as e:
            print(f"Error reading TS/JS file {file_path}: {e}")

    def run_comprehensive_check(self, repos_dir: Path = Path("./repos")):
        """Run comprehensive check on all relevant files"""
        print("🔍 Comprehensive UI Spelling Check")
        print("=" * 60)
        
        for repo_dir in repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue
                
            print(f"\n📁 Checking repository: {repo_dir.name}")
            
            # Check JSON translation files
            locale_dirs = repo_dir.rglob("**/i18n/locales/en")
            for locale_dir in locale_dirs:
                if locale_dir.is_dir():
                    for json_file in locale_dir.glob("*.json"):
                        print(f"  📄 {json_file.relative_to(repo_dir)}")
                        self.check_json_file(json_file)
            
            # Check Vue files
            for vue_file in repo_dir.rglob("*.vue"):
                if 'node_modules' not in str(vue_file):
                    self.check_vue_file(vue_file)
            
            # Check selected TypeScript/JavaScript files that might have user text
            critical_dirs = ['src/shared/services', 'src/views', 'src/components']
            for dir_pattern in critical_dirs:
                for ts_file in repo_dir.rglob(f"{dir_pattern}/**/*.ts"):
                    if 'node_modules' not in str(ts_file):
                        self.check_ts_js_file(ts_file)
        
        # Report findings
        self.report_findings()

    def report_findings(self):
        """Report all found errors"""
        print(f"\n" + "=" * 60)
        print(f"📊 SPELLING AND GRAMMAR ERRORS FOUND")
        print(f"=" * 60)
        
        if not self.found_errors:
            print("✅ No misspellings found in user-facing text!")
            return
        
        # Group by type
        by_type = {}
        for error in self.found_errors:
            error_type = error['type']
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(error)
        
        for error_type, errors in by_type.items():
            print(f"\n🔴 {error_type.upper()} ERRORS ({len(errors)} found):")
            print("-" * 40)
            
            for i, error in enumerate(errors, 1):
                file_path = error['file'].replace('/Users/alex/Documents/Projects/src-graph/repos/', '')
                print(f"\n{i}. {file_path}")
                print(f"   Context: {error['context']}")
                print(f"   Text: \"{error['full_text']}\"")
                print(f"   Error: '{error['error']}' → '{error['correction']}'")
        
        print(f"\n📈 Summary: {len(self.found_errors)} total errors found")

def main():
    checker = UISpellChecker()
    checker.run_comprehensive_check()

if __name__ == "__main__":
    main()