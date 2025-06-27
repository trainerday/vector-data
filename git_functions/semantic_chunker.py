#!/usr/bin/env python3
"""
Semantic Code Chunker - Splits code by logical boundaries
"""

import re
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class SemanticChunk:
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'component', 'block'
    name: str  # function/class name if detected

class SemanticCodeChunker:
    def __init__(self, max_lines: int = 100):
        self.max_lines = max_lines
        
        # Language-specific patterns
        self.patterns = {
            'typescript': {
                'function': [
                    r'^(\s*)(export\s+)?(async\s+)?function\s+(\w+)',
                    r'^(\s*)(export\s+)?const\s+(\w+)\s*=\s*(async\s+)?\(',
                    r'^(\s*)(\w+)\s*\([^)]*\)\s*{',  # method in class
                ],
                'class': [
                    r'^(\s*)(export\s+)?(abstract\s+)?class\s+(\w+)',
                    r'^(\s*)(export\s+)?interface\s+(\w+)',
                    r'^(\s*)(export\s+)?type\s+(\w+)',
                ],
                'component': [
                    r'^(\s*)(export\s+)?(default\s+)?function\s+(\w+).*React',
                    r'^(\s*)const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{',  # React functional component
                ],
                'block': [
                    r'^(\s*)(if|for|while|switch|try)\s*\(',
                    r'^(\s*)(export\s+)?(default\s+)?{',
                ]
            },
            'javascript': {
                'function': [
                    r'^(\s*)(async\s+)?function\s+(\w+)',
                    r'^(\s*)const\s+(\w+)\s*=\s*(async\s+)?\(',
                    r'^(\s*)(\w+)\s*\([^)]*\)\s*{',
                ],
                'class': [
                    r'^(\s*)class\s+(\w+)',
                ],
                'block': [
                    r'^(\s*)(if|for|while|switch|try)\s*\(',
                    r'^(\s*)(module\.exports|exports)\s*=',
                ]
            },
            'python': {
                'function': [
                    r'^(\s*)def\s+(\w+)',
                    r'^(\s*)async\s+def\s+(\w+)',
                ],
                'class': [
                    r'^(\s*)class\s+(\w+)',
                ],
                'block': [
                    r'^(\s*)(if|for|while|with|try)\s+',
                ]
            }
        }

    def detect_chunk_boundaries(self, content: str, language: str) -> List[Tuple[int, str, str]]:
        """
        Detect logical boundaries in code
        Returns: List of (line_number, chunk_type, name)
        """
        lines = content.split('\n')
        boundaries = [(0, 'start', '')]  # Always start at line 0
        
        lang_patterns = self.patterns.get(language, self.patterns['javascript'])
        
        for line_num, line in enumerate(lines):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                continue
            
            # Check each pattern type
            for chunk_type, patterns in lang_patterns.items():
                for pattern in patterns:
                    match = re.match(pattern, line)
                    if match:
                        # Extract name from match groups
                        name = ''
                        for group in match.groups():
                            if group and re.match(r'^\w+$', group):
                                name = group
                                break
                        
                        boundaries.append((line_num, chunk_type, name))
                        break
                
                if boundaries and boundaries[-1][0] == line_num:
                    break  # Found a match, don't check other types
        
        return boundaries

    def find_chunk_end(self, lines: List[str], start_line: int, language: str) -> int:
        """Find the end of a logical chunk based on indentation and braces"""
        if start_line >= len(lines):
            return len(lines) - 1
        
        start_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        brace_count = 0
        paren_count = 0
        
        # For brace-based languages
        if language in ['typescript', 'javascript', 'java', 'c', 'cpp']:
            for i in range(start_line, len(lines)):
                line = lines[i]
                brace_count += line.count('{') - line.count('}')
                
                # If we've closed all braces, this might be the end
                if i > start_line and brace_count <= 0:
                    return i
                
                # Don't go too long
                if i - start_line > self.max_lines:
                    return i
        
        # For indentation-based languages (Python)
        elif language == 'python':
            for i in range(start_line + 1, len(lines)):
                line = lines[i]
                if line.strip():  # Non-empty line
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= start_indent:
                        return i - 1
                
                if i - start_line > self.max_lines:
                    return i
        
        # Fallback: look for significant indentation decrease
        else:
            for i in range(start_line + 1, len(lines)):
                line = lines[i]
                if line.strip():
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent < start_indent and i > start_line + 5:
                        return i - 1
                
                if i - start_line > self.max_lines:
                    return i
        
        return min(start_line + self.max_lines, len(lines) - 1)

    def chunk_code(self, content: str, language: str) -> List[SemanticChunk]:
        """Split code into semantic chunks"""
        lines = content.split('\n')
        boundaries = self.detect_chunk_boundaries(content, language)
        chunks = []
        
        for i, (start_line, chunk_type, name) in enumerate(boundaries):
            # Determine end line
            if i < len(boundaries) - 1:
                # Next boundary exists
                next_start = boundaries[i + 1][0]
                end_line = min(
                    self.find_chunk_end(lines, start_line, language),
                    next_start - 1
                )
            else:
                # Last chunk
                end_line = self.find_chunk_end(lines, start_line, language)
            
            # Ensure minimum chunk size
            if end_line - start_line < 3 and i < len(boundaries) - 1:
                continue
            
            # Extract chunk content
            chunk_lines = lines[start_line:end_line + 1]
            chunk_content = '\n'.join(chunk_lines)
            
            # Skip empty chunks
            if not chunk_content.strip():
                continue
            
            chunks.append(SemanticChunk(
                content=chunk_content,
                start_line=start_line + 1,  # 1-indexed
                end_line=end_line + 1,      # 1-indexed
                chunk_type=chunk_type,
                name=name
            ))
        
        return chunks

def demo_semantic_chunking():
    """Demonstrate semantic chunking on sample code"""
    
    sample_ts = '''
export interface User {
  id: string
  email: string
}

export class UserService {
  private users: User[] = []
  
  async createUser(email: string): Promise<User> {
    const user = {
      id: Math.random().toString(),
      email
    }
    this.users.push(user)
    return user
  }
  
  async getUser(id: string): Promise<User | null> {
    return this.users.find(u => u.id === id) || null
  }
  
  private validateEmail(email: string): boolean {
    return email.includes('@')
  }
}

export const userApi = {
  async login(credentials) {
    if (!credentials.email) {
      throw new Error('Email required')
    }
    return authenticate(credentials)
  }
}
'''
    
    chunker = SemanticCodeChunker(max_lines=50)
    chunks = chunker.chunk_code(sample_ts, 'typescript')
    
    print("🔍 Semantic Chunking Demo")
    print("=" * 50)
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}: {chunk.chunk_type.upper()}")
        if chunk.name:
            print(f"Name: {chunk.name}")
        print(f"Lines: {chunk.start_line}-{chunk.end_line} ({chunk.end_line - chunk.start_line + 1} lines)")
        print(f"Content preview:")
        preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
        print(f"```\n{preview}\n```")
        print("-" * 30)

if __name__ == "__main__":
    demo_semantic_chunking()