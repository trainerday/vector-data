#!/usr/bin/env python3
"""
Simple script to update all repositories with latest changes
"""

from git.incremental_indexer import IncrementalIndexer

def main():
    print("🔄 Updating all repositories with latest changes...")
    
    indexer = IncrementalIndexer()
    results = indexer.update_all_repositories(pull_latest=True)
    
    total_chunks = sum(results.values())
    
    print(f"\n✅ Update complete!")
    print(f"📊 Summary:")
    for repo, chunks in results.items():
        status = "✨ Updated" if chunks > 0 else "✓ No changes"
        print(f"  {status}: {repo} ({chunks} chunks)")
    
    if total_chunks > 0:
        print(f"\n🎯 Total: {total_chunks} new/updated chunks indexed")
        print(f"💡 Try: python search_cli.py 'your search query'")
    else:
        print(f"\n😴 All repositories are up to date!")

if __name__ == "__main__":
    main()