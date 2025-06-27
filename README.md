# Source Code Vector Database

A ChromaDB-based vector database for semantic search across multiple GitHub repositories.

## Features

- Clone and index multiple GitHub repositories
- Semantic search using OpenAI embeddings
- Support for 20+ programming languages
- Respects .gitignore patterns
- CLI interface for easy searching
- Persistent vector storage with ChromaDB

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Required API Keys:**
   - `OPENAI_API_KEY`: For generating embeddings
   - `GITHUB_TOKEN`: For accessing private repositories (optional)

## Usage

### Initial Setup (First Time)

```bash
# Index repositories for the first time
python index_repos.py https://github.com/your-org/api-project.git https://github.com/your-org/web-project.git
```

### Keep Repositories Updated

```bash
# Update all repositories with latest changes (recommended)
python git/update_repos.py

# Update specific repository
python git/incremental_indexer.py --repo main-app-web

# Update all repositories
python git/incremental_indexer.py --all

# Check for changes without pulling from remote
python git/incremental_indexer.py --all --no-pull
```

### Search Code

```python
# Search across all repositories
results = vectorizer.search_code("user authentication", n_results=10)

# Search within specific repository
results = vectorizer.search_code("API endpoints", repo_filter="api-project")
```

### CLI Search

```bash
# Basic search
python search_cli.py "user authentication"

# Search with filters
python search_cli.py "database connection" --repo api-project --num-results 5

# Show database stats
python search_cli.py "query" --stats
```

## Supported Languages

- Python, JavaScript, TypeScript
- Java, Go, Rust, C/C++
- C#, Ruby, PHP, Swift
- Kotlin, Scala, Clojure
- HTML, CSS, SQL, JSON
- Markdown, YAML, Dockerfile
- And more...

## Configuration

### Chunking Strategy
- Code is split into chunks of ~1000 tokens
- Preserves line numbers and context
- Handles large files efficiently

### Ignored Files
- Follows .gitignore patterns
- Skips common build/cache directories
- Limits file size to 1MB

## Database Schema

Each code chunk includes:
- `content`: The actual code
- `file_path`: Relative path within repository
- `repo_name`: Repository identifier
- `start_line`/`end_line`: Line numbers
- `language`: Programming language
- `indexed_at`: Timestamp

## How It Works

### Incremental Updates
- **Tracks file changes** using Git commit hashes and file content hashes
- **Only processes changed files** since last indexing
- **Removes chunks** for deleted files automatically
- **Updates metadata** to track repository state

### Update Process
1. **Git pull** latest changes from remote
2. **Compare commit hashes** to detect changes
3. **Check file hashes** for modified files
4. **Remove old chunks** for changed/deleted files
5. **Index new chunks** for modified files
6. **Update metadata** with new hashes and timestamps

## Performance

- Uses `text-embedding-3-small` model (1536 dimensions)
- Persistent ChromaDB storage with incremental updates
- Efficient similarity search
- Only re-indexes changed files (much faster updates)
- Handles multiple repositories seamlessly

## Example Queries

- "authentication middleware"
- "database connection pooling"
- "error handling patterns"
- "API rate limiting"
- "user validation logic"
- "configuration management"