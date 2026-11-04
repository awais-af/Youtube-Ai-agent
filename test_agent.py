"""
Unit and integration tests for the YouTube Tutorial Agent.
Verifies URL parsing, metadata fetching, transcript chunking, and mock LLM integration.
"""

import unittest
from yt_agent.extractor import extract_video_id, fetch_video_metadata
from yt_agent.transcript_processor import ProcessedTranscript, format_timestamp


class TestYouTubeExtractor(unittest.TestCase):

    def test_extract_video_id_standard(self):
        url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
        self.assertEqual(extract_video_id(url), "kqtD5dpn9C8")

    def test_extract_video_id_short_url(self):
        url = "https://youtu.be/kqtD5dpn9C8?t=120"
        self.assertEqual(extract_video_id(url), "kqtD5dpn9C8")

    def test_extract_video_id_embed(self):
        url = "https://www.youtube.com/embed/kqtD5dpn9C8"
        self.assertEqual(extract_video_id(url), "kqtD5dpn9C8")

    def test_extract_video_id_shorts(self):
        url = "https://www.youtube.com/shorts/kqtD5dpn9C8"
        self.assertEqual(extract_video_id(url), "kqtD5dpn9C8")

    def test_extract_video_id_raw(self):
        self.assertEqual(extract_video_id("kqtD5dpn9C8"), "kqtD5dpn9C8")

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(0), "00:00")
        self.assertEqual(format_timestamp(65), "01:05")
        self.assertEqual(format_timestamp(3665), "01:01:05")

    def test_processed_transcript(self):
        mock_raw = [
            {"text": "Welcome to Python tutorial", "start": 0.0, "duration": 4.0},
            {"text": "Today we learn variables", "start": 5.0, "duration": 3.0},
            {"text": "Variables store data in memory", "start": 95.0, "duration": 4.0},
        ]
        processed = ProcessedTranscript(mock_raw, interval_seconds=60)
        self.assertEqual(processed.total_segments, 3)
        self.assertIn("Welcome to Python tutorial", processed.full_text)
        self.assertIn("[00:00]", processed.timestamped_text)
        self.assertIn("[01:35]", processed.timestamped_text)

        # Test search
        results = processed.search("variables")
        self.assertGreaterEqual(len(results), 1)

    def test_oembed_metadata(self):
        metadata = fetch_video_metadata("kqtD5dpn9C8")
        self.assertIn("Python", metadata.get("title", ""))
        self.assertEqual(metadata.get("video_id"), "kqtD5dpn9C8")

    def test_safe_parse_json(self):
        from yt_agent.fact_checker import _safe_parse_json
        
        # Markdown fenced json
        fenced = "```json\n[{\"claim\": \"test\", \"status\": \"still_valid\"}]\n```"
        parsed = _safe_parse_json(fenced)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["status"], "still_valid")

        # Commentary prefix
        prefix = "Here is the result:\n{\"needs_verification\": false}\nHope that helps!"
        parsed_obj = _safe_parse_json(prefix)
        self.assertFalse(parsed_obj["needs_verification"])

        # Fallback on garbage
        self.assertEqual(_safe_parse_json("invalid", default=[]), [])

    def test_pdf_generation(self):
        from yt_agent.pdf_generator import generate_tutorial_pdf
        from pypdf import PdfReader
        import io

        dummy_meta = {
            "title": "Build LangChain App with Python",
            "author_name": "AI Engineer",
            "duration": "15:30",
            "video_id": "test123"
        }
        dummy_fc = {
            "needs_verification": True,
            "claims": [
                {
                    "claim": "Import ChatOpenAI from langchain.chat_models",
                    "status": "outdated",
                    "explanation": "In modern LangChain, chat models have moved to langchain-openai.",
                    "corrected_info": "from langchain_openai import ChatOpenAI",
                    "sources": ["https://python.langchain.com/"],
                    "timestamp": "[02:15]"
                },
                {
                    "claim": "Install packages using pip install langchain",
                    "status": "still_valid",
                    "explanation": "pip install langchain remains the official package installation command.",
                    "corrected_info": "",
                    "sources": ["https://pypi.org/project/langchain/"],
                    "timestamp": "[00:45]"
                }
            ]
        }
        pdf_bytes = generate_tutorial_pdf(
            metadata=dummy_meta,
            description_text="This tutorial explains how to build a LangChain app.",
            curriculum_text="Module 1: Setup\nModule 2: Coding",
            fact_check_data=dummy_fc
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        
        reader = PdfReader(io.BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_web_search_empty_query(self):
        from yt_agent.web_search import web_search
        self.assertEqual(web_search(""), [])
        self.assertEqual(web_search("   "), [])


if __name__ == "__main__":
    unittest.main()

