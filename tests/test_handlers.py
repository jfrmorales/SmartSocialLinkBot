import unittest
from dotenv import load_dotenv
import os

# Load environment variables for testing
load_dotenv(dotenv_path="config/.env")

from handlers import final_normalize_url as normalize_url

class TestURLNormalization(unittest.TestCase):

    def test_normalize_instagram_url(self):
        self.assertEqual(normalize_url("https://instagram.com/user"), "https://ddinstagram.com/user")

    def test_normalize_twitter_url(self):
        self.assertEqual(normalize_url("https://twitter.com/user"), "https://fixupx.com/user")

    def test_normalize_x_url(self):
        self.assertEqual(normalize_url("https://x.com/user"), "https://fixupx.com/user")

    def test_normalize_tiktok_url(self):
        self.assertEqual(normalize_url("https://tiktok.com/user"), "https://vxtiktok.com/user")

    def test_normalize_with_subdomain(self):
        self.assertEqual(normalize_url("https://vm.tiktok.com/user"), "https://vm.vxtiktok.com/user")

    def test_no_normalization_needed(self):
        self.assertEqual(normalize_url("https://google.com"), "https://google.com")

    def test_malformed_url(self):
        self.assertEqual(normalize_url("not a url"), "not a url")

    def test_already_normalized_url(self):
        self.assertEqual(normalize_url("https://ddinstagram.com/user"), "https://ddinstagram.com/user")

if __name__ == '__main__':
    unittest.main()