#!/usr/bin/env python3
"""
Incremental Source Code Indexer
Updates the vector database with only changed files
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
import argparse

from git import Repo  # GitPython
from git_functions.src_vectorizer import SourceVectorizer

class IncrementalIndexer:
    def __init__(self, db_path: str = "./chroma_db", repos_dir: str = "./git_functions/repos"):
        # Get the parent directory of this script
        script_dir = Path(__file__).parent
        # Convert to absolute paths relative to script location
        db_path = str((script_dir / db_path).resolve())
        print(f"Using ChromaDB at: {db_path}")
        self.vectorizer = SourceVectorizer(db_path=db_path)
        self.repos_dir = (script_dir / repos_dir).resolve()
        self.metadata_file = Path(db_path) / "repo_metadata.json"
        self.repo_metadata = self.load_metadata()

    def load_metadata(self) -> Dict:
        """Load repository metadata (last commit hashes, file hashes)"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def save_metadata(self):
        """Save repository metadata"""
        self.metadata_file.parent.mkdir(exist_ok=True)
        with open(self.metadata_file, 'w') as f:
            json.dump(self.repo_metadata, f, indent=2)

    def get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""

    def get_repo_commit_hash(self, repo_path: Path) -> str:
        """Get current commit hash of repository"""
        try:
            repo = Repo(repo_path)
            return repo.head.commit.hexsha
        except:
            return ""

    def pull_latest(self, repo_name: str) -> bool:
        """Pull latest changes from remote repository"""
        repo_path = self.repos_dir / repo_name
        
        if not repo_path.exists():
            print(f"Repository {repo_name} not found at {repo_path}")
            return False

        try:
            repo = Repo(repo_path)
            print(f"Pulling latest changes for {repo_name}...")
            
            # Fetch and pull latest changes
            origin = repo.remotes.origin
            origin.fetch()
            repo.git.pull()
            
            print(f"Successfully pulled latest changes for {repo_name}")
            return True
        except Exception as e:
            print(f"Error pulling repository {repo_name}: {e}")
            return False

    def get_changed_files(self, repo_name: str) -> Tuple[List[Path], List[str], str]:
        """
        Get list of changed files since last indexing
        Returns: (changed_files, deleted_files, current_commit_hash)
        """
        repo_path = self.repos_dir / repo_name
        current_commit = self.get_repo_commit_hash(repo_path)
        
        # Get stored metadata for this repo
        repo_meta = self.repo_metadata.get(repo_name, {})
        last_commit = repo_meta.get('last_commit', '')
        stored_file_hashes = repo_meta.get('file_hashes', {})
        
        changed_files = []
        deleted_files = []
        
        if not last_commit or last_commit != current_commit:
            print(f"Commit changed from {last_commit[:8]} to {current_commit[:8]}")
            
            # Check all code files for changes
            gitignore_spec = self.vectorizer.get_gitignore_spec(str(repo_path))
            
            # Track current files
            current_files = set()
            
            for file_path in repo_path.rglob('*'):
                if not file_path.is_file():
                    continue
                    
                if not self.vectorizer.should_process_file(file_path, gitignore_spec):
                    continue
                
                relative_path = str(file_path.relative_to(repo_path))
                current_files.add(relative_path)
                
                # Check if file hash changed
                current_hash = self.get_file_hash(file_path)
                stored_hash = stored_file_hashes.get(relative_path)
                
                if current_hash != stored_hash:
                    changed_files.append(file_path)
                    print(f"  Changed: {relative_path}")
            
            # Find deleted files
            for stored_file in stored_file_hashes.keys():
                if stored_file not in current_files:
                    deleted_files.append(stored_file)
                    print(f"  Deleted: {stored_file}")
        
        return changed_files, deleted_files, current_commit

    def remove_deleted_chunks(self, repo_name: str, deleted_files: List[str]):
        """Remove chunks for deleted files from the database"""
        if not deleted_files:
            return
            
        print(f"Removing chunks for {len(deleted_files)} deleted files...")
        
        # Get all chunk IDs for deleted files
        all_metadata = self.vectorizer.collection.get()
        chunk_ids_to_delete = []
        
        for i, metadata in enumerate(all_metadata['metadatas']):
            if (metadata.get('repo_name') == repo_name and 
                metadata.get('file_path') in deleted_files):
                chunk_ids_to_delete.append(all_metadata['ids'][i])
        
        if chunk_ids_to_delete:
            self.vectorizer.collection.delete(ids=chunk_ids_to_delete)
            print(f"Removed {len(chunk_ids_to_delete)} chunks for deleted files")

    def update_repository(self, repo_name: str, pull_latest: bool = True) -> int:
        """
        Update a specific repository with only changed files
        Returns number of chunks processed
        """
        repo_path = self.repos_dir / repo_name
        
        if not repo_path.exists():
            print(f"Repository {repo_name} not found. Use full indexing first.")
            return 0
        
        # Pull latest changes if requested
        if pull_latest:
            if not self.pull_latest(repo_name):
                return 0
        
        # Get changed files
        changed_files, deleted_files, current_commit = self.get_changed_files(repo_name)
        
        if not changed_files and not deleted_files:
            print(f"No changes detected in {repo_name}")
            return 0
        
        print(f"Processing {len(changed_files)} changed files and {len(deleted_files)} deleted files")
        
        # Remove chunks for deleted files
        self.remove_deleted_chunks(repo_name, deleted_files)
        
        # Process changed files
        chunks_processed = 0
        updated_file_hashes = self.repo_metadata.get(repo_name, {}).get('file_hashes', {})
        
        for file_path in changed_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                if not content.strip():
                    continue
                    
                language = self.vectorizer.code_extensions[file_path.suffix]
                relative_path = str(file_path.relative_to(repo_path))
                
                # Remove old chunks for this file first
                all_metadata = self.vectorizer.collection.get()
                old_chunk_ids = []
                
                for i, metadata in enumerate(all_metadata['metadatas']):
                    if (metadata.get('repo_name') == repo_name and 
                        metadata.get('file_path') == relative_path):
                        old_chunk_ids.append(all_metadata['ids'][i])
                
                if old_chunk_ids:
                    self.vectorizer.collection.delete(ids=old_chunk_ids)
                
                # Create new chunks
                chunks = self.vectorizer.chunk_code(content, relative_path, repo_name, language)
                
                for chunk in chunks:
                    embedding = self.vectorizer.get_embedding(chunk.content)
                    if embedding is None:
                        continue
                        
                    self.vectorizer.collection.add(
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
                
                # Update file hash
                updated_file_hashes[relative_path] = self.get_file_hash(file_path)
                
                if chunks_processed % 10 == 0 and chunks_processed > 0:
                    print(f"Processed {chunks_processed} chunks...")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        # Update metadata
        if repo_name not in self.repo_metadata:
            self.repo_metadata[repo_name] = {}
        
        self.repo_metadata[repo_name].update({
            'last_commit': current_commit,
            'file_hashes': updated_file_hashes,
            'last_updated': datetime.now().isoformat()
        })
        
        # Remove hashes for deleted files
        for deleted_file in deleted_files:
            updated_file_hashes.pop(deleted_file, None)
        
        self.save_metadata()
        
        print(f"Incremental update complete: {chunks_processed} chunks processed")
        return chunks_processed

    def update_all_repositories(self, pull_latest: bool = True) -> Dict[str, int]:
        """Update all known repositories"""
        results = {}
        
        # Get all repositories from directory
        for repo_dir in self.repos_dir.iterdir():
            if repo_dir.is_dir() and (repo_dir / '.git').exists():
                repo_name = repo_dir.name
                print(f"\n{'='*60}")
                print(f"Updating repository: {repo_name}")
                print(f"{'='*60}")
                
                chunks = self.update_repository(repo_name, pull_latest)
                results[repo_name] = chunks
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Incremental repository indexer")
    parser.add_argument("--repo", help="Specific repository to update")
    parser.add_argument("--all", action="store_true", help="Update all repositories")
    parser.add_argument("--no-pull", action="store_true", help="Skip git pull, just check for changes")
    parser.add_argument("--db-path", default="./chroma_db", help="Database path")
    parser.add_argument("--repos-dir", default="./git_functions/repos", help="Repositories directory")
    
    args = parser.parse_args()
    
    indexer = IncrementalIndexer(db_path=args.db_path, repos_dir=args.repos_dir)
    pull_latest = not args.no_pull
    
    if args.repo:
        chunks = indexer.update_repository(args.repo, pull_latest)
        print(f"\nProcessed {chunks} chunks for {args.repo}")
    elif args.all:
        results = indexer.update_all_repositories(pull_latest)
        total_chunks = sum(results.values())
        print(f"\n{'='*60}")
        print(f"UPDATE SUMMARY")
        print(f"{'='*60}")
        for repo, chunks in results.items():
            print(f"{repo}: {chunks} chunks")
        print(f"Total: {total_chunks} chunks")
    else:
        print("Specify --repo <name> or --all to update repositories")
        
        # Show current status
        stats = indexer.vectorizer.get_stats()
        print(f"\nCurrent database stats:")
        print(f"  - {stats['total_chunks']} chunks")
        print(f"  - {len(stats['repositories'])} repositories: {', '.join(stats['repositories'])}")

if __name__ == "__main__":
    main()