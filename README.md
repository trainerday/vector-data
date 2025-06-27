# Source Code Vector Database

A ChromaDB-based vector database for semantic search includes data ingestion from
 - multiple GitHub repositories.
 - mixpanel or other user event data 
 - forums
 - clicky
 - email?
 - youtube videos?
 - blog posts
 - main wordpress
 - telegram
 - github issues





## Features for git / code base

- Clone and index multiple GitHub repositories
- Semantic search using OpenAI embeddings
- Support for 20+ programming languages
- Respects .gitignore patterns
- CLI interface for easy searching
- Persistent vector storage with ChromaDB

## Features for Mixpanel data

- Smart incremental downloading from last existing file to yesterday
- Automatic detection of missing days
- Rate-limited API calls to respect Mixpanel limits
- Configurable date ranges for historical data
- Overwrite option for incomplete data files

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
python git/index_repos.py https://github.com/your-org/api-project.git https://github.com/your-org/web-project.git
```

### Keep Repositories Updated

```bash
# Update all repositories with latest changes (recommended)
python git/update_repos.py

# Update specific repository
python git_incremental_indexer.py --repo main-app-web

# Update all repositories
python git_incremental_indexer.py --all

# Check for changes without pulling from remote
python git_incremental_indexer.py --all --no-pull
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
python git/search_cli.py "user authentication"

# Search with filters
python git/search_cli.py "database connection" --repo api-project --num-results 5

# Show database stats
python git/search_cli.py "query" --stats
```

### Mixpanel Data Download

```bash
# Incremental download (from last file to yesterday) - DEFAULT MODE
python get_mixpanel_data.py

# Force re-download of yesterday's data (useful if data was incomplete)
python get_mixpanel_data.py --overwrite-last

# Full download with custom date range
python get_mixpanel_data.py --mode full --start-date 2024-01-01 --end-date 2024-12-31

# Check available options
python get_mixpanel_data.py --help
```

**Incremental Mode Behavior:**
- If run today (June 27), it will check for yesterday (June 26)
- If June 26 file exists: "Already up to date!" 
- If June 26 file missing: Downloads June 26 data
- With `--overwrite-last`: Always re-downloads the last existing file

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