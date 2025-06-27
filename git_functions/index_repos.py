#!/usr/bin/env python3
"""
Script to index multiple GitHub repositories
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports when running from git_functions/
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from git_functions.src_vectorizer import SourceVectorizer

def main():
    parser = argparse.ArgumentParser(description="Index GitHub repositories")
    parser.add_argument("repos", nargs="+", help="GitHub repository URLs")
    parser.add_argument("--db-path", default="../chroma_db", help="Database path (default: ../chroma_db)")
    parser.add_argument("--repos-dir", default="./repos", help="Local repos directory (default: ./repos)")
    parser.add_argument("--skip-clone", action="store_true", help="Skip cloning, use existing local repos")
    
    args = parser.parse_args()
    
    # Create directories
    Path(args.repos_dir).mkdir(exist_ok=True)
    
    try:
        vectorizer = SourceVectorizer(db_path=args.db_path)
        total_chunks = 0
        
        for repo_url in args.repos:
            print(f"\n{'='*60}")
            print(f"Processing: {repo_url}")
            print(f"{'='*60}")
            
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            local_path = Path(args.repos_dir) / repo_name
            
            if not args.skip_clone:
                if not vectorizer.clone_repo(repo_url, str(local_path)):
                    print(f"Failed to clone {repo_url}, skipping...")
                    continue
            else:
                if not local_path.exists():
                    print(f"Local repository not found: {local_path}")
                    continue
            
            chunks = vectorizer.index_repository(str(local_path), repo_name)
            total_chunks += chunks
            
        print(f"\n{'='*60}")
        print(f"INDEXING COMPLETE")
        print(f"{'='*60}")
        print(f"Total chunks indexed: {total_chunks}")
        
        # Show final stats
        stats = vectorizer.get_stats()
        print(f"Database contains:")
        print(f"  - {stats['total_chunks']} code chunks")
        print(f"  - {len(stats['repositories'])} repositories: {', '.join(stats['repositories'])}")
        print(f"  - {len(stats['languages'])} languages: {', '.join(sorted(stats['languages']))}")
        
        print(f"\nYou can now search using:")
        print(f"  python search_cli.py 'your search query'")
        
    except KeyboardInterrupt:
        print("\nIndexing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during indexing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()