import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import os

from ai_pr_insight.fetcher import GitHubPRCommentsFetcher
from ai_pr_insight.analyzer import PRCommentsAnalyzer
from ai_pr_insight.summarizer import PRAnalysisSummarizer, SummaryConfig

class TestGitHubPRCommentsFetcher(unittest.TestCase):
    @patch("requests.get")
    def setUp(self, mock_get):
        """Set up test environment with mocked requests."""
        # Mock the response for the username fetch
        mock_response = MagicMock()
        mock_response.json.return_value = {"login": "testuser"}
        mock_get.return_value = mock_response
        
        self.token = "fake_token"
        self.year = 2023
        self.fetcher = GitHubPRCommentsFetcher(token=self.token, year=self.year)

    def test_initialization(self):
        """Test that the fetcher initializes correctly."""
        self.assertEqual(self.fetcher.year, 2023)
        self.assertEqual(self.fetcher.headers["Authorization"], "Bearer fake_token")
        self.assertEqual(self.fetcher.username, "testuser")

    @patch("requests.get")
    def test_get_username(self, mock_get):
        """Test fetching the authenticated user's username."""
        # Setup a new mock for this specific test
        mock_response = MagicMock()
        mock_response.json.return_value = {"login": "differentuser"}
        mock_get.return_value = mock_response

        # We need to call the method directly to test it with the new mock
        username = self.fetcher._get_username()
        self.assertEqual(username, "differentuser")
        mock_get.assert_called_once_with(
            "https://api.github.com/user", 
            headers=self.fetcher.headers
        )

# Keep the rest of the test classes unchanged
class TestPRCommentsAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.analyzer = PRCommentsAnalyzer(batch_size=10)

    def test_initialization(self):
        """Test that the analyzer initializes correctly."""
        self.assertEqual(self.analyzer.batch_size, 10)

    def test_normalize_item(self):
        """Test normalization of checklist items."""
        item = "  [Code Quality] Check for unused variables  "
        normalized = self.analyzer.normalize_item(item)
        self.assertEqual(normalized, "code quality check for unused variables")

    def test_parse_checklist_items(self):
        """Test parsing checklist items from text."""
        text = """
        [Code Quality] Check for unused variables
        [Documentation] Ensure all functions are documented
        """
        items = self.analyzer.parse_checklist_items(text)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["category"], "Code Quality")
        self.assertEqual(items[1]["description"], "Ensure all functions are documented")

class TestPRAnalysisSummarizer(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.config = SummaryConfig(similarity_threshold=0.90, batch_size=50)
        self.summarizer = PRAnalysisSummarizer(self.config)

    def test_initialization(self):
        """Test that the summarizer initializes correctly."""
        self.assertEqual(self.summarizer.config.similarity_threshold, 0.90)
        self.assertEqual(self.summarizer.config.batch_size, 50)

    def test_load_json_files(self):
        """Test loading JSON files from a directory."""
        # Create a temporary JSON file
        test_dir = Path("test_data")
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "test.json"
        with open(test_file, "w") as f:
            json.dump([{"category": "Code Quality", "description": "Check for unused variables"}], f)

        # Test loading
        items = self.summarizer.load_json_files(test_dir)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["category"], "Code Quality")

        # Clean up
        os.remove(test_file)
        os.rmdir(test_dir)

if __name__ == "__main__":
    unittest.main()
