#!/usr/bin/env python3
"""
CLI interface for searching the source code vector database
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports when running from git_functions/
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from git_functions.src_vectorizer import SourceVectorizer

def main():
    parser = argparse.ArgumentParser(description="Search source code vector database")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-n", "--num-results", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("-r", "--repo", help="Filter by repository name")
    parser.add_argument("--db-path", default="../chroma_db", help="Database path (default: ../chroma_db)")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    if not Path(args.db_path).exists():
        print(f"Database not found at {args.db_path}")
        print("Run the indexer first to create the database.")
        sys.exit(1)
    
    try:
        vectorizer = SourceVectorizer(db_path=args.db_path)
        
        if args.stats:
            stats = vectorizer.get_stats()
            print("=== Database Statistics ===")
            print(f"Total chunks: {stats['total_chunks']}")
            print(f"Repositories: {', '.join(stats['repositories'])}")
            print(f"Languages: {', '.join(stats['languages'])}")
            print()
        
        print(f"Searching for: '{args.query}'")
        if args.repo:
            print(f"Repository filter: {args.repo}")
        print("=" * 50)
        
        results = vectorizer.search_code(args.query, n_results=args.num_results, repo_filter=args.repo)
        
        if not results:
            print("No results found.")
            return
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            print(f"\n[{i}] {metadata['repo_name']}/{metadata['file_path']}")
            print(f"    Lines: {metadata['start_line']}-{metadata['end_line']} | Language: {metadata['language']}")
            if 'distance' in result and result['distance']:
                print(f"    Similarity: {1 - result['distance']:.3f}")
            
            # Show content with line numbers
            content_lines = result['content'].split('\n')
            for j, line in enumerate(content_lines[:10], metadata['start_line']):  # Show first 10 lines
                print(f"    {j:4d}: {line}")
            
            if len(content_lines) > 10:
                print(f"    ... ({len(content_lines) - 10} more lines)")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()