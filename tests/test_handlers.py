import unittest
from unittest.mock import patch, mock_open
from dotenv import load_dotenv
import os

# Load environment variables for testing
load_dotenv(dotenv_path="config/.env")

# Mocked JSON data for testing
MOCK_MAPPINGS = {
    "instagram.com": "ddinstagram.com",
    "twitter.com": "fixupx.com",
    "x.com": "fixupx.com",
    "tiktok.com": "vxtiktok.com",
    "fixupx.com": "fixupx.com"
}

class TestURLNormalization(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_normalize_instagram_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://instagram.com/user"), "https://ddinstagram.com/user")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_normalize_twitter_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://twitter.com/user"), "https://fixupx.com/user")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_normalize_x_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://x.com/user"), "https://fixupx.com/user")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_normalize_tiktok_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://tiktok.com/user"), "https://vxtiktok.com/user")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_normalize_with_subdomain(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://vm.tiktok.com/user"), "https://vm.vxtiktok.com/user")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_no_normalization_needed(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://google.com"), "https://google.com")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_malformed_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("not a url"), "not a url")

    @patch("builtins.open", new_callable=mock_open, read_data='{"instagram.com": "ddinstagram.com", "twitter.com": "fixupx.com", "x.com": "fixupx.com", "tiktok.com": "vxtiktok.com", "fixupx.com": "fixupx.com"}')
    def test_already_normalized_url(self, mock_file):
        from handlers import normalize_url
        self.assertEqual(normalize_url("https://ddinstagram.com/user"), "https://ddinstagram.com/user")

if __name__ == '__main__':
    unittest.main()
