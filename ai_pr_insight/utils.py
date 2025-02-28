import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Dict, Any

def setup_logging() -> logging.Logger:
    """Set up logging with optional debug mode."""
    log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ai_pr_insight.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def load_env_vars() -> Dict[str, Any]:
    """Load and validate environment variables."""
    load_dotenv()
    return {
        'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'CACHE_EXPIRATION_MINUTES': int(os.getenv('CACHE_EXPIRATION_MINUTES', 120)),
        'DEBUG': os.getenv('DEBUG', 'false').lower() == 'true',
        'SOURCE_CODE_LINES_OFFSET': int(os.getenv('SOURCE_CODE_LINES_OFFSET', 3)),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'ERROR').upper(),
    }

def ensure_dir_exists(path: str) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    Path(path).mkdir(parents=True, exist_ok=True)

def validate_file_path(path: str) -> bool:
    """Validate that a file path exists and is accessible."""
    return Path(path).exists()

def format_timestamp(timestamp: str) -> str:
    """Format a timestamp for consistent logging."""
    from datetime import datetime
    return datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
