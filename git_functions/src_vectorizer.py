#!/usr/bin/env python3
"""
Source Code Vector Database using ChromaDB
Indexes multiple GitHub repositories for semantic search
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import chromadb
from chromadb.config import Settings
import openai
from git import Repo
import tiktoken
from pathspec import PathSpec
from dotenv import load_dotenv

load_dotenv()

@dataclass
class CodeChunk:
    content: str
    file_path: str
    repo_name: str
    start_line: int
    end_line: int
    language: str
    chunk_id: str

class SourceVectorizer:
    def __init__(self, db_path: str = "../chroma_db", openai_api_key: str = None):
        self.db_path = db_path
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.openai_api_key
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=True)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="source_code",
            metadata={"description": "Source code embeddings"}
        )
        
        # Initialize tokenizer for chunking
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-3-small")
        
        # File extensions to process
        self.code_extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.sh': 'bash',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.less': 'less',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.dockerfile': 'dockerfile',
            '.tf': 'terraform'
        }
        
        # Default gitignore patterns to skip
        self.default_ignore_patterns = [
            'node_modules/**',
            '.git/**',
            '__pycache__/**',
            '*.pyc',
            'venv/**',
            '.env',
            '.env.*',
            'build/**',
            'dist/**',
            'target/**',
            '.next/**',
            '.nuxt/**',
            'coverage/**',
            '*.log',
            '*.tmp',
            '*.temp',
            '.DS_Store',
            'Thumbs.db'
        ]

    def clone_repo(self, repo_url: str, local_path: str) -> str:
        """Clone a GitHub repository"""
        print(f"Cloning {repo_url} to {local_path}...")
        
        if os.path.exists(local_path):
            print(f"Repository already exists at {local_path}")
            return local_path
            
        try:
            # Add GitHub token to URL if available
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token and "github.com" in repo_url:
                if repo_url.startswith("https://github.com/"):
                    repo_url = repo_url.replace("https://github.com/", f"https://{github_token}@github.com/")
                    
            Repo.clone_from(repo_url, local_path)
            print(f"Successfully cloned {repo_url}")
            return local_path
        except Exception as e:
            print(f"Error cloning repository: {e}")
            return None

    def get_gitignore_spec(self, repo_path: str) -> PathSpec:
        """Load .gitignore patterns"""
        gitignore_path = Path(repo_path) / '.gitignore'
        patterns = self.default_ignore_patterns.copy()
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                patterns.extend(line.strip() for line in f if line.strip() and not line.startswith('#'))
        
        return PathSpec.from_lines('gitwildmatch', patterns)

    def should_process_file(self, file_path: Path, gitignore_spec: PathSpec) -> bool:
        """Check if file should be processed"""
        # Check extension
        if file_path.suffix not in self.code_extensions:
            return False
            
        # Check gitignore
        if gitignore_spec.match_file(str(file_path)):
            return False
            
        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                return False
        except:
            return False
            
        return True

    def chunk_code(self, content: str, file_path: str, repo_name: str, language: str, max_tokens: int = 1000) -> List[CodeChunk]:
        """Split code into chunks"""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            line_tokens = len(self.tokenizer.encode(line))
            
            if current_tokens + line_tokens > max_tokens and current_chunk:
                # Create chunk
                chunk_content = '\n'.join(current_chunk)
                chunk_id = hashlib.md5(f"{repo_name}:{file_path}:{start_line}:{i-1}".encode()).hexdigest()
                
                chunks.append(CodeChunk(
                    content=chunk_content,
                    file_path=file_path,
                    repo_name=repo_name,
                    start_line=start_line,
                    end_line=i-1,
                    language=language,
                    chunk_id=chunk_id
                ))
                
                current_chunk = [line]
                current_tokens = line_tokens
                start_line = i
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunk_id = hashlib.md5(f"{repo_name}:{file_path}:{start_line}:{len(lines)}".encode()).hexdigest()
            
            chunks.append(CodeChunk(
                content=chunk_content,
                file_path=file_path,
                repo_name=repo_name,
                start_line=start_line,
                end_line=len(lines),
                language=language,
                chunk_id=chunk_id
            ))
        
        return chunks

    def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text"""
        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def index_repository(self, repo_path: str, repo_name: str = None) -> int:
        """Index a repository"""
        if repo_name is None:
            repo_name = Path(repo_path).name
            
        print(f"Indexing repository: {repo_name}")
        
        gitignore_spec = self.get_gitignore_spec(repo_path)
        chunks_processed = 0
        
        for file_path in Path(repo_path).rglob('*'):
            if not file_path.is_file():
                continue
                
            if not self.should_process_file(file_path, gitignore_spec):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                if not content.strip():
                    continue
                    
                language = self.code_extensions[file_path.suffix]
                relative_path = str(file_path.relative_to(repo_path))
                
                chunks = self.chunk_code(content, relative_path, repo_name, language)
                
                for chunk in chunks:
                    embedding = self.get_embedding(chunk.content)
                    if embedding is None:
                        continue
                        
                    self.collection.add(
                        ids=[chunk.chunk_id],
                        embeddings=[embedding],
                        documents=[chunk.content],
                        metadatas=[{
                            'file_path': chunk.file_path,
                            'repo_name': chunk.repo_name,
                            'start_line': chunk.start_line,
                            'end_line': chunk.end_line,
                            'language': chunk.language,
                            'indexed_at': datetime.now().isoformat()
                        }]
                    )
                    chunks_processed += 1
                    
                    if chunks_processed % 10 == 0:
                        print(f"Processed {chunks_processed} chunks...")
                        
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        print(f"Finished indexing {repo_name}: {chunks_processed} chunks")
        return chunks_processed

    def search_code(self, query: str, n_results: int = 10, repo_filter: str = None) -> List[Dict]:
        """Search code using semantic similarity"""
        embedding = self.get_embedding(query)
        if embedding is None:
            return []
            
        where_clause = {}
        if repo_filter:
            where_clause = {"repo_name": repo_filter}
            
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
            
        return formatted_results

    def get_stats(self) -> Dict:
        """Get database statistics"""
        count = self.collection.count()
        
        # Get unique repos
        all_metadata = self.collection.get()['metadatas']
        repos = set(meta['repo_name'] for meta in all_metadata)
        
        # Get languages
        languages = set(meta['language'] for meta in all_metadata)
        
        return {
            'total_chunks': count,
            'repositories': list(repos),
            'languages': list(languages)
        }

def main():
    """Example usage"""
    vectorizer = SourceVectorizer()
    
    # Example: Clone and index repositories
    repos = [
        "https://github.com/your-org/api-project.git",
        "https://github.com/your-org/web-project.git"
    ]
    
    for repo_url in repos:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        local_path = f"./repos/{repo_name}"
        
        if vectorizer.clone_repo(repo_url, local_path):
            vectorizer.index_repository(local_path, repo_name)
    
    # Search example
    print("\n=== Search Results ===")
    results = vectorizer.search_code("user authentication", n_results=5)
    
    for result in results:
        print(f"\nFile: {result['metadata']['repo_name']}/{result['metadata']['file_path']}")
        print(f"Lines: {result['metadata']['start_line']}-{result['metadata']['end_line']}")
        print(f"Language: {result['metadata']['language']}")
        print(f"Content preview: {result['content'][:200]}...")
        print("-" * 50)
    
    # Show stats
    stats = vectorizer.get_stats()
    print(f"\n=== Database Stats ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Repositories: {', '.join(stats['repositories'])}")
    print(f"Languages: {', '.join(stats['languages'])}")

if __name__ == "__main__":
    main()