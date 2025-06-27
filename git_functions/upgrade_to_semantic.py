#!/usr/bin/env python3
"""
Upgrade existing vector database to use semantic chunking
Replaces token-based chunks with function/class-based chunks
"""

import os
import json
import hashlib
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add parent directory to path for imports when running from git_functions/
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from git_functions.src_vectorizer import SourceVectorizer
from git_functions.semantic_chunker import SemanticCodeChunker, SemanticChunk

class SemanticVectorizer(SourceVectorizer):
    """Enhanced vectorizer with semantic chunking"""
    
    def __init__(self, db_path: str = "../chroma_db", openai_api_key: str = None):
        super().__init__(db_path, openai_api_key)
        self.semantic_chunker = SemanticCodeChunker(max_lines=100)
        
        # Map file extensions to language names for semantic chunker
        self.extension_to_language = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'javascript',  # Similar brace structure
            '.c': 'javascript',
            '.h': 'javascript',
            '.hpp': 'javascript',
            '.cs': 'javascript',
            '.rb': 'python',       # Similar indentation
            '.php': 'javascript',
            '.swift': 'javascript',
            '.kt': 'javascript',
            '.scala': 'javascript',
        }

    def chunk_code_semantically(self, content: str, file_path: str, repo_name: str, language: str) -> List[Dict]:
        """Create semantic chunks with proper metadata"""
        
        # Map language to semantic chunker language
        semantic_language = self.extension_to_language.get(
            Path(file_path).suffix, 
            'javascript'  # Default fallback
        )
        
        # Get semantic chunks
        semantic_chunks = self.semantic_chunker.chunk_code(content, semantic_language)
        
        chunks = []
        for chunk in semantic_chunks:
            # Create unique chunk ID including semantic info
            chunk_id = hashlib.md5(
                f"{repo_name}:{file_path}:{chunk.start_line}:{chunk.end_line}:{chunk.chunk_type}:{chunk.name}".encode()
            ).hexdigest()
            
            chunks.append({
                'chunk_id': chunk_id,
                'content': chunk.content,
                'metadata': {
                    'file_path': file_path,
                    'repo_name': repo_name,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'language': language,
                    'chunk_type': chunk.chunk_type,
                    'function_name': chunk.name,
                    'lines_count': chunk.end_line - chunk.start_line + 1,
                    'indexed_at': datetime.now().isoformat(),
                    'chunking_method': 'semantic'
                }
            })
        
        return chunks

    def index_repository_semantic(self, repo_path: str, repo_name: str = None) -> int:
        """Index repository using semantic chunking"""
        if repo_name is None:
            repo_name = Path(repo_path).name
            
        print(f"Indexing repository with semantic chunking: {repo_name}")
        
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
                
                # Create semantic chunks
                chunks = self.chunk_code_semantically(content, relative_path, repo_name, language)
                
                for chunk in chunks:
                    embedding = self.get_embedding(chunk['content'])
                    if embedding is None:
                        continue
                        
                    self.collection.add(
                        ids=[chunk['chunk_id']],
                        embeddings=[embedding],
                        documents=[chunk['content']],
                        metadatas=[chunk['metadata']]
                    )
                    chunks_processed += 1
                    
                    if chunks_processed % 10 == 0:
                        print(f"Processed {chunks_processed} semantic chunks...")
                        
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        print(f"Finished semantic indexing {repo_name}: {chunks_processed} chunks")
        return chunks_processed

def upgrade_database():
    """Upgrade existing database to semantic chunking"""
    
    print("🔄 UPGRADING TO SEMANTIC CHUNKING")
    print("=" * 60)
    
    # Initialize vectorizer
    vectorizer = SemanticVectorizer()
    
    print("\n1️⃣ Backing up current database stats...")
    old_stats = vectorizer.get_stats()
    print(f"   Current: {old_stats['total_chunks']} chunks")
    print(f"   Repositories: {', '.join(old_stats['repositories'])}")
    
    print("\n2️⃣ Clearing existing chunks...")
    # Get all chunk IDs and delete them
    all_data = vectorizer.collection.get()
    if all_data['ids']:
        vectorizer.collection.delete(ids=all_data['ids'])
        print(f"   Deleted {len(all_data['ids'])} old chunks")
    else:
        print("   No existing chunks to delete")
    print("   ✅ Old token-based chunks removed")
    
    print("\n3️⃣ Re-indexing with semantic chunking...")
    repos_dir = Path("./repos")
    total_chunks = 0
    
    for repo_dir in repos_dir.iterdir():
        if repo_dir.is_dir() and (repo_dir / '.git').exists():
            repo_name = repo_dir.name
            print(f"\n   📦 Processing {repo_name}...")
            
            chunks = vectorizer.index_repository_semantic(str(repo_dir), repo_name)
            total_chunks += chunks
    
    print(f"\n4️⃣ Updating metadata...")
    # Clear old metadata and rebuild
    metadata_file = Path("./chroma_db/repo_metadata.json")
    if metadata_file.exists():
        metadata_file.unlink()
    
    # Run metadata builder
    os.system("python build_metadata.py")
    
    print(f"\n✅ UPGRADE COMPLETE!")
    print("=" * 60)
    
    # Show new stats
    new_stats = vectorizer.get_stats()
    print(f"📊 NEW DATABASE STATS:")
    print(f"   Chunks: {old_stats['total_chunks']} → {new_stats['total_chunks']}")
    print(f"   Method: Token-based → Semantic")
    print(f"   Repositories: {len(new_stats['repositories'])}")
    print(f"   Languages: {len(new_stats['languages'])}")
    
    print(f"\n🎯 IMPROVEMENTS:")
    print(f"   ✅ Functions and classes are complete chunks")
    print(f"   ✅ Better search context and results")
    print(f"   ✅ Metadata includes function names and types")
    print(f"   ✅ More logical code boundaries")
    
    print(f"\n🚀 TEST IT OUT:")
    print(f"   python search_cli.py 'user authentication'")
    print(f"   python search_cli.py 'database connection' --repo main-app-api")

def preview_semantic_chunking():
    """Preview how semantic chunking will work on a sample file"""
    
    repos_dir = Path("./repos")
    vectorizer = SemanticVectorizer()
    
    print("🔍 SEMANTIC CHUNKING PREVIEW")
    print("=" * 50)
    
    # Find a TypeScript file to preview
    for repo_dir in repos_dir.iterdir():
        if not repo_dir.is_dir():
            continue
            
        for file_path in repo_dir.rglob('*.ts'):
            if 'node_modules' in str(file_path) or file_path.name.endswith('.d.ts'):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if len(content) > 500 and len(content) < 5000:  # Good size for demo
                    relative_path = str(file_path.relative_to(repo_dir))
                    
                    print(f"📄 Sample file: {repo_dir.name}/{relative_path}")
                    print(f"📏 Size: {len(content)} chars, {len(content.split())} lines")
                    print()
                    
                    chunks = vectorizer.chunk_code_semantically(
                        content, relative_path, repo_dir.name, 'typescript'
                    )
                    
                    print(f"🧩 Semantic chunks: {len(chunks)}")
                    print("-" * 40)
                    
                    for i, chunk in enumerate(chunks[:5], 1):  # Show first 5
                        meta = chunk['metadata']
                        chunk_type = meta['chunk_type'].upper()
                        func_name = meta['function_name']
                        lines = meta['lines_count']
                        
                        print(f"Chunk {i}: {chunk_type}")
                        if func_name:
                            print(f"  Name: {func_name}")
                        print(f"  Lines: {meta['start_line']}-{meta['end_line']} ({lines} lines)")
                        print(f"  Preview: {chunk['content'][:100]}...")
                        print()
                    
                    if len(chunks) > 5:
                        print(f"  ... and {len(chunks) - 5} more chunks")
                    
                    return  # Found good example
                    
            except Exception as e:
                continue
    
    print("No suitable sample file found for preview")

def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        preview_semantic_chunking()
    else:
        upgrade_database()

if __name__ == "__main__":
    main()