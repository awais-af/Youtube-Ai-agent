"""
YouTube Video Tutorial Agent Package.
Extracts knowledge, code, roadmaps, and timestamped answers from YouTube tutorials.
"""

from yt_agent.agent import YouTubeTutorialAgent
from yt_agent.extractor import (
    extract_video_id,
    fetch_video_metadata,
    fetch_transcript,
    YouTubeExtractorError,
    TranscriptUnavailableError,
    InvalidYouTubeURLError
)
from yt_agent.llm_provider import LLMProvider, LLMProviderError
from yt_agent.transcript_processor import ProcessedTranscript, format_timestamp
from yt_agent.web_search import web_search
from yt_agent.fact_checker import FactCheckAgent
from yt_agent.pdf_generator import generate_tutorial_pdf

__all__ = [
    "YouTubeTutorialAgent",
    "extract_video_id",
    "fetch_video_metadata",
    "fetch_transcript",
    "YouTubeExtractorError",
    "TranscriptUnavailableError",
    "InvalidYouTubeURLError",
    "LLMProvider",
    "LLMProviderError",
    "ProcessedTranscript",
    "format_timestamp",
    "web_search",
    "FactCheckAgent",
    "generate_tutorial_pdf",
]

