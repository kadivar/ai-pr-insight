import os
import requests
from dotenv import load_dotenv
import logging

class GitHubAPIDiagnostic:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG

    def debug_github_api(self) -> None:
        """Run diagnostics to test GitHub API access and authentication."""
        load_dotenv()
        token = os.getenv('GITHUB_TOKEN')
        
        if not token:
            self.logger.error("No GITHUB_TOKEN found in .env file")
            return
            
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        base_url = 'https://api.github.com'
        
        self.logger.info("=== GitHub API Access Diagnostic ===\n")
        
        # Test 1: Check authentication
        self.logger.info("1. Testing Authentication...")
        try:
            response = requests.get(f'{base_url}/user', headers=headers)
            response.raise_for_status()
            user_data = response.json()
            self.logger.info(f"✓ Successfully authenticated as: {user_data['login']}")
            self.logger.info(f"User ID: {user_data['id']}")
            self.logger.info(f"Account type: {user_data['type']}")
        except Exception as e:
            self.logger.error(f"✗ Authentication failed: {str(e)}")
            if hasattr(response, 'json'):
                self.logger.error(f"API Response: {response.json()}")
            return

        # Test 2: Check rate limit
        self.logger.info("\n2. Checking Rate Limits...")
        try:
            response = requests.get(f'{base_url}/rate_limit', headers=headers)
            response.raise_for_status()
            limits = response.json()
            self.logger.info("✓ Rate limits:")
            self.logger.info(f"Core: {limits['resources']['core']['remaining']}/{limits['resources']['core']['limit']}")
            self.logger.info(f"Search: {limits['resources']['search']['remaining']}/{limits['resources']['search']['limit']}")
        except Exception as e:
            self.logger.error(f"✗ Failed to check rate limits: {str(e)}")

        # Test 3: List repositories
        self.logger.info("\n3. Testing Repository Access...")
        try:
            response = requests.get(
                f'{base_url}/user/repos',
                headers=headers,
                params={
                    'per_page': 5,
                    'affiliation': 'owner,collaborator,organization_member'
                }
            )
            response.raise_for_status()
            repos = response.json()
            self.logger.info(f"✓ Successfully retrieved repositories")
            self.logger.info("First 5 accessible repositories:")
            for repo in repos:
                self.logger.info(f"- {repo['full_name']} ({repo['private'] and 'Private' or 'Public'})")
        except Exception as e:
            self.logger.error(f"✗ Failed to list repositories: {str(e)}")
            if hasattr(response, 'json'):
                self.logger.error(f"API Response: {response.json()}")

        # Test 4: List organizations
        self.logger.info("\n4. Testing Organization Access...")
        try:
            response = requests.get(f'{base_url}/user/orgs', headers=headers)
            response.raise_for_status()
            orgs = response.json()
            self.logger.info(f"✓ Successfully retrieved organizations")
            self.logger.info("Organizations:")
            for org in orgs:
                self.logger.info(f"- {org['login']}")
        except Exception as e:
            self.logger.error(f"✗ Failed to list organizations: {str(e)}")
            if hasattr(response, 'json'):
                self.logger.error(f"API Response: {response.json()}")

        self.logger.info("\n=== Diagnostic Complete ===")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    diagnostic = GitHubAPIDiagnostic()
    diagnostic.debug_github_api()
