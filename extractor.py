"""
YouTube Video Information and Transcript Extractor.
Extracts video metadata and timestamped transcripts from YouTube URLs.
"""

import re
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

try:
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable
    )
except ImportError:
    YouTubeTranscriptApi = None
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception
    VideoUnavailable = Exception


class YouTubeExtractorError(Exception):
    """Base exception for extractor errors."""
    pass


class InvalidYouTubeURLError(YouTubeExtractorError):
    """Raised when an invalid YouTube URL or ID is provided."""
    pass


class TranscriptUnavailableError(YouTubeExtractorError):
    """Raised when subtitles/transcripts are disabled or unavailable."""
    pass


def extract_video_id(url_or_id: str) -> str:
    """
    Extracts the 11-character YouTube video ID from various URL formats or raw ID.
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - Raw 11-character ID
    """
    if not url_or_id:
        raise InvalidYouTubeURLError("Empty URL or Video ID provided.")

    clean_str = url_or_id.strip()

    # If it's already an 11-character alphanumeric/dash/underscore string
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", clean_str):
        return clean_str

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|embed\/|shorts\/|live\/)([0-9A-Za-z_-]{11})",
        r"[?&]v=([0-9A-Za-z_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean_str)
        if match:
            return match.group(1)

    raise InvalidYouTubeURLError(f"Could not extract a valid YouTube video ID from: '{url_or_id}'")


def fetch_video_metadata(video_id: str) -> Dict[str, Any]:
    """
    Fetches public metadata for a YouTube video using YouTube's oEmbed endpoint.
    Requires no API key.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(video_url)}&format=json"

    metadata = {
        "video_id": video_id,
        "video_url": video_url,
        "title": f"YouTube Video ({video_id})",
        "author_name": "Unknown Creator",
        "author_url": "",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
    }

    try:
        req = urllib.request.Request(
            oembed_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            metadata["title"] = data.get("title", metadata["title"])
            metadata["author_name"] = data.get("author_name", metadata["author_name"])
            metadata["author_url"] = data.get("author_url", metadata["author_url"])
            if data.get("thumbnail_url"):
                metadata["thumbnail_url"] = data.get("thumbnail_url")
    except Exception as e:
        # Graceful fallback: return basic metadata with standard thumbnail
        metadata["fetch_warning"] = str(e)

    return metadata


def fetch_transcript(
    video_id: str,
    preferred_languages: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Fetches transcript segments for a given video ID with timestamps.
    Returns a list of dicts: [{'text': str, 'start': float, 'duration': float}, ...]
    """
    if YouTubeTranscriptApi is None:
        raise YouTubeExtractorError(
            "youtube-transcript-api is not installed. Please run 'pip install youtube-transcript-api'."
        )

    langs = preferred_languages or ["en", "en-US", "en-GB"]

    try:
        # Check if YouTubeTranscriptApi has instance or class methods
        api_instance = YouTubeTranscriptApi() if hasattr(YouTubeTranscriptApi, "__init__") else YouTubeTranscriptApi

        # First attempt: directly fetch with preferred languages
        if hasattr(api_instance, "fetch"):
            try:
                res = api_instance.fetch(video_id, languages=langs)
                return res.to_raw_data() if hasattr(res, "to_raw_data") else list(res)
            except Exception:
                pass
        elif hasattr(YouTubeTranscriptApi, "get_transcript"):
            try:
                return YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
            except Exception:
                pass

        # Second attempt: list transcripts and find any available (or translate to English)
        transcript_list = None
        if hasattr(api_instance, "list"):
            transcript_list = api_instance.list(video_id)
        elif hasattr(YouTubeTranscriptApi, "list_transcripts"):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        if transcript_list:
            # Try to find transcript in desired languages
            try:
                found_t = transcript_list.find_transcript(langs)
                data = found_t.fetch()
                return data if isinstance(data, list) else data.to_raw_data()
            except Exception:
                pass

            # Try to find any transcript and translate to English
            for tr in transcript_list:
                try:
                    if tr.is_translatable:
                        translated = tr.translate("en")
                        data = translated.fetch()
                        return data if isinstance(data, list) else data.to_raw_data()
                    else:
                        data = tr.fetch()
                        return data if isinstance(data, list) else data.to_raw_data()
                except Exception:
                    continue

        # Third attempt: fallback to fetching without language filter
        if hasattr(api_instance, "fetch"):
            res = api_instance.fetch(video_id)
            return res.to_raw_data() if hasattr(res, "to_raw_data") else list(res)

        raise TranscriptUnavailableError(
            f"No transcript or captions could be retrieved for video '{video_id}'."
        )

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise TranscriptUnavailableError(
            f"Subtitles/Transcripts are disabled or not available for this YouTube video ({video_id})."
        ) from e
    except VideoUnavailable as e:
        raise YouTubeExtractorError(f"Video {video_id} is unavailable or private.") from e
    except Exception as e:
        if isinstance(e, YouTubeExtractorError):
            raise e
        raise TranscriptUnavailableError(
            f"Failed to retrieve transcript for video {video_id}: {str(e)}"
        ) from e
