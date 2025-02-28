import requests
from datetime import datetime, timedelta
import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import logging

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Log to stdout
)

class GitHubPRCommentsFetcher:
    def __init__(
        self,
        token: str,
        year: int,
        month: Optional[int] = None,
        cache_expiration_minutes: int = 60,
        target_username: Optional[str] = None,
        target_org: Optional[str] = None
    ):
        """
        Initialize the fetcher with your GitHub personal access token and filters.

        Args:
            token (str): GitHub personal access token
            year (int): Year to filter comments
            month (int, optional): Month to filter comments (1-12). If None, only year is used.
            cache_expiration_minutes (int): Cache expiration time in minutes
            target_username (str, optional): Specific username to fetch PRs for. If None, uses authenticated user
            target_org (str, optional): Specific organization to fetch repos from. If None, fetches from all accessible repos
        """
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.target_username = target_username
        self.username = target_username if target_username else self._get_username()
        self.target_org = target_org
        self.year = year
        self.month = month
        self.cache_file = Path("cache") / "repositories.json"
        self.cache_expiration_minutes = cache_expiration_minutes

    def _get_username(self) -> str:
        """Get the authenticated user's username."""
        response = requests.get(f'{self.base_url}/user', headers=self.headers)
        response.raise_for_status()
        return response.json()['login']

    def _is_cache_valid(self) -> bool:
        """Check if the cached data is valid based on expiration time."""
        if not self.cache_file.exists():
            return False
        cache_mtime = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        expiration_time = cache_mtime + timedelta(minutes=self.cache_expiration_minutes)
        return datetime.now() <= expiration_time

    def _load_cache(self) -> List[Dict]:
        """Load cached repositories with validation."""
        logger.debug(f"Loading cache from {self.cache_file}")
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if not isinstance(cache_data, list):
                    raise ValueError("Cached data is not a list")
                logger.debug(f"Cache data: {cache_data[:5]}")
                return cache_data
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return []

    def _save_cache(self, repositories: List[Dict]):
        """Save repositories to cache."""
        self.cache_file.parent.mkdir(exist_ok=True)  # Ensure cache directory exists
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(repositories, f, indent=2)

    def get_all_accessible_repositories(self) -> List[Dict]:
        """
        Get all repositories the user has access to, using cache when valid.
        If target_org is specified, only fetch repositories from that organization.
        """
        if self._is_cache_valid():
            logger.debug("Using cached repository data...")
            repos = self._load_cache()
            if self.target_org:
                repos = [r for r in repos if r['full_name'].startswith(f"{self.target_org}/")]
            return repos

        logger.debug("Fetching all accessible repositories...")
        repositories = []
        page = 1

        # Determine the API endpoint based on whether we're fetching org repos or user repos
        if self.target_org:
            api_endpoint = f'{self.base_url}/orgs/{self.target_org}/repos'
            logger.debug(f"Fetching repositories for organization: {self.target_org}")
        else:
            api_endpoint = f'{self.base_url}/user/repos'
            logger.debug("Fetching all accessible repositories")

        while True:
            try:
                response = requests.get(
                    api_endpoint,
                    headers=self.headers,
                    params={
                        'page': page,
                        'per_page': 100,
                        'type': 'all',  # Include all types of repositories
                        'sort': 'updated',
                        'direction': 'desc'
                    }
                )
                response.raise_for_status()
                repos = response.json()
                if not repos:
                    break
                repositories.extend(repos)
                logger.debug(f"Fetched page {page} - Found {len(repos)} repositories")
                page += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching repositories: {e}")
                break

        logger.debug(f"Total repositories found: {len(repositories)}")
        self._save_cache(repositories)  # Save results to cache
        return repositories

    def get_repository_prs(self, repo_full_name: str) -> List[Dict]:
        """Get all pull requests in a repository where the user is the creator and author."""
        prs = []
        page = 1

        logger.debug(f"Fetching PRs for repository: {repo_full_name} (Filtered by year {self.year})")
        
        while True:
            try:
                response = requests.get(
                    f'{self.base_url}/repos/{repo_full_name}/pulls',
                    headers=self.headers,
                    params={
                        'state': 'all',  # Fetch both open and closed PRs
                        'author': self.username,  # Filter by the user (only PRs created by the user)
                        'page': page,
                        'per_page': 100
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Break if no more PRs are returned
                if not data:
                    logger.debug(f"No more PRs on page {page}")
                    break

                for pr in data:
                    # Extract author login and creator login
                    pr_author = pr.get('user', {}).get('login', '')

                    # Check if this PR belongs to the user (author is same as creator)
                    if pr_author == self.username:
                        created_at = datetime.fromisoformat(pr['created_at'].replace("Z", "+00:00"))

                        # Skip PRs not in the target year
                        if created_at.year != self.year:
                            logger.debug(f"Skipping PR #{pr['number']} (Created: {created_at})")
                            continue

                        prs.append(pr)

                # Stop fetching pages if PRs are older than the target year
                if data and datetime.fromisoformat(data[-1]['created_at'].replace("Z", "+00:00")).year < self.year:
                    logger.debug(f"Stopping fetch: All remaining PRs are older than {self.year}")
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching PRs for {repo_full_name}: {e}")
                break

        logger.debug(f"Found {len(prs)} PRs for repository {repo_full_name} (Filtered by year {self.year})")
        return prs

    def get_pr_comments(self, repo_full_name: str, pr_number: int) -> List[Dict]:
        """Get all comments for a specific pull request, including source code snippets."""
        all_comments = []
        
        # Get issue comments (no source code context here)
        try:
            page = 1
            while True:
                response = requests.get(
                    f'{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments',
                    headers=self.headers,
                    params={'page': page, 'per_page': 100}
                )
                response.raise_for_status()
                comments = response.json()
                if not comments:
                    break
                all_comments.extend(comments)
                page += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching issue comments: {e}")

        # Get review comments (these include source code context)
        try:
            page = 1
            while True:
                response = requests.get(
                    f'{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/comments',
                    headers=self.headers,
                    params={'page': page, 'per_page': 100}
                )
                response.raise_for_status()
                comments = response.json()
                if not comments:
                    break

                for comment in comments:
                    # Fetch the source code snippet
                    source_code = self._get_source_code_snippet(
                        repo_full_name,
                        comment.get('path'),
                        comment.get('position'),
                        comment.get('line'),
                        comment  # Pass the entire comment object
                    )
                    comment['source_code'] = source_code
                    all_comments.append(comment)

                page += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching review comments: {e}")

        return all_comments

    def _get_source_code_snippet(self, repo_full_name: str, file_path: str, position: int, line: int, comment: dict) -> str:
        """
        Fetch the source code snippet for a given comment.
        Primarily uses the diff_hunk field when available, falling back to other methods if needed.
        """
        # First try to use the diff_hunk if available
        if comment.get('diff_hunk'):
            # Clean up the diff markers and return the context
            lines = comment['diff_hunk'].split('\n')
            # Remove diff markers but keep the actual code
            cleaned_lines = [line.lstrip('+-') for line in lines if not line.startswith(('@@', '---', '+++'))]
            if cleaned_lines:
                return '\n'.join(cleaned_lines)

        # If no diff_hunk, try the original file content approach
        if not file_path:
            return None

        try:
            response = requests.get(
                f'{self.base_url}/repos/{repo_full_name}/contents/{file_path}',
                headers=self.headers
            )
            response.raise_for_status()
            file_data = response.json()

            # Handle symbolic links
            if file_data.get('type') == 'symlink':
                response = requests.get(
                    f'{self.base_url}/repos/{repo_full_name}/contents/{file_data["target"]}',
                    headers=self.headers
                )
                response.raise_for_status()
                file_data = response.json()

            # Decode the file content
            import base64
            file_content = base64.b64decode(file_data['content']).decode('utf-8')
            file_lines = file_content.splitlines()

            # Use line number if available
            snippet_lines_count_offset = os.getenv('SOURCE_CODE_LINES_OFFSET', 3)

            if line is not None:
                snippet_start = max(0, line - snippet_lines_count_offset)
                snippet_end = min(len(file_lines), line + snippet_lines_count_offset)
                return '\n'.join(file_lines[snippet_start:snippet_end])

            # Use position if line is not available
            if position is not None:
                snippet_start = max(0, position - snippet_lines_count_offset)
                snippet_end = min(len(file_lines), position + snippet_lines_count_offset)
                return '\n'.join(file_lines[snippet_start:snippet_end])

            return None

        except Exception as e:
            logger.error(f"Error processing source code: {e}")
            return None

    def fetch_all_pr_comments(self) -> List[Dict]:
        """Fetch all comments on all pull requests created by the authenticated user."""
        formatted_comments = []
        repositories = self.get_all_accessible_repositories()
        total_comments = 0

        for repo in tqdm(repositories, desc="Processing Repositories"):
            repo_full_name = repo['full_name']
            prs = self.get_repository_prs(repo_full_name)

            for pr in tqdm(prs, desc=f"Processing PRs in {repo_full_name}", leave=False):
                comments = self.get_pr_comments(repo_full_name, pr['number'])

                for comment in comments:
                    if comment['user']['login'] == self.username:
                        continue
                    try:
                        comment_date = datetime.fromisoformat(comment['created_at'].replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    # Filter by year and month
                    if comment_date.year != self.year or (self.month is not None and comment_date.month != self.month):
                        continue
                    formatted_comments.append({
                        'author': comment['user']['login'],
                        'repository': repo_full_name,
                        'pr_number': pr['number'],
                        'pr_title': pr['title'],
                        'pr_url': pr['html_url'],
                        'datetime': comment['created_at'],
                        'message': comment['body'],
                        'comment_url': comment['html_url'],
                        'permalink': comment['html_url'],
                        'source_code': comment.get('source_code')
                    })
                    total_comments += 1

        logger.debug(f"Total comments fetched: {total_comments}")
        return formatted_comments

    def save_comments_to_file(self, comments: List[Dict], output_path: str):
        """Save comments to a JSON file, ensuring the directory exists."""
        output_path = Path(output_path)
        
        # Ensure directory exists
        if not output_path.parent.exists():
            logger.debug(f"Creating directory: {output_path.parent}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2)
        
        logger.debug(f"Comments saved to {output_path}")
