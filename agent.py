"""
YouTube Tutorial AI Agent Brain.
Coordinates video transcript ingestion, timestamp indexing, and educational LLM generation.
"""

from typing import Dict, Any, List, Optional, Generator, Union
from yt_agent.extractor import extract_video_id, fetch_video_metadata, fetch_transcript
from yt_agent.transcript_processor import ProcessedTranscript
from yt_agent.llm_provider import LLMProvider, LLMProviderError
from yt_agent.prompts import (
    SYSTEM_TUTOR_PROMPT,
    CURRICULUM_PROMPT,
    CODE_EXTRACTION_PROMPT,
    STUDY_GUIDE_PROMPT,
    QUIZ_PROMPT,
    QA_PROMPT,
    VIDEO_DESCRIPTION_PROMPT,
)


class YouTubeTutorialAgent:
    """
    Intelligent Agent that analyzes YouTube tutorial videos,
    explains concepts step-by-step with timestamps, extracts runnable code,
    and conducts interactive Q&A.
    """

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider_name = provider
        self.llm = LLMProvider(provider=provider, api_key=api_key, model=model)
        self.metadata: Optional[Dict[str, Any]] = None
        self.transcript: Optional[ProcessedTranscript] = None
        self.chat_history: List[Dict[str, str]] = []
        
        # Caches for generated reports
        self._description_cache: Optional[str] = None
        self._curriculum_cache: Optional[str] = None
        self._code_cache: Optional[str] = None
        self._notes_cache: Optional[str] = None
        self._quiz_cache: Optional[str] = None
        self._fact_check_cache: Optional[Dict[str, Any]] = None

    def switch_provider(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None):
        """Switches LLM provider between Groq and OpenAI."""
        self.provider_name = provider
        self.llm.switch_provider(provider=provider, api_key=api_key, model=model)

    def is_loaded(self) -> bool:
        """Returns True if a video transcript has been loaded."""
        return self.transcript is not None and self.metadata is not None

    def load_video(self, url_or_id: str) -> Dict[str, Any]:
        """
        Loads a YouTube tutorial by URL or ID.
        Fetches metadata and timestamped transcript segments.
        """
        video_id = extract_video_id(url_or_id)
        metadata = fetch_video_metadata(video_id)
        raw_segments = fetch_transcript(video_id)

        self.metadata = metadata
        self.transcript = ProcessedTranscript(raw_segments)
        self.chat_history = []
        
        # Reset caches
        self._description_cache = None
        self._curriculum_cache = None
        self._code_cache = None
        self._notes_cache = None
        self._quiz_cache = None
        self._fact_check_cache = None

        return self.get_video_info()

    def get_video_info(self) -> Dict[str, Any]:
        """Returns metadata and transcript metrics for the loaded video."""
        if not self.is_loaded():
            return {}

        stats = self.transcript.get_summary_stats()
        return {
            "video_id": self.metadata.get("video_id"),
            "video_url": self.metadata.get("video_url"),
            "title": self.metadata.get("title"),
            "author_name": self.metadata.get("author_name"),
            "thumbnail_url": self.metadata.get("thumbnail_url"),
            "duration": stats["duration"],
            "total_segments": stats["total_segments"],
            "total_words": stats["total_words"],
            "total_blocks": stats["total_blocks"],
        }

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise ValueError("No video loaded. Please call `load_video(url)` first.")

    def _build_context(self, max_chars: int = 14000) -> str:
        """
        Prepares timestamped transcript text suitable for model context window
        and respects free-tier TPM/ITPM rate limits (~7000 tokens).
        """
        self._ensure_loaded()
        text = self.transcript.timestamped_text
        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n[... Remaining transcript available in video: {self.transcript.duration_str} total ...]"
        return text

    def explain(
        self,
        question: str,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        Answers a user question about the tutorial with timestamp citations.
        Supports both streaming and non-streaming modes.
        """
        self._ensure_loaded()
        context = self._build_context()

        prompt_content = QA_PROMPT.format(
            video_title=self.metadata.get("title", "Tutorial"),
            author_name=self.metadata.get("author_name", "Creator"),
            duration=self.transcript.duration_str,
            transcript_context=context,
            question=question
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": prompt_content}
        ]

        if stream:
            return self.llm.generate_stream(messages)
        return self.llm.generate(messages)

    def chat(
        self,
        user_message: str,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """
        Multi-turn chat session with conversational memory grounded in the video tutorial.
        """
        self._ensure_loaded()
        context = self._build_context()

        system_instruction = (
            f"{SYSTEM_TUTOR_PROMPT}\n\n"
            f"You are tutoring the user on the video: '{self.metadata.get('title')}' by {self.metadata.get('author_name')}.\n"
            f"Total duration: {self.transcript.duration_str}.\n"
            f"TIMESTAMPED TRANSCRIPT REFERENCE:\n{context}"
        )

        messages = [{"role": "system", "content": system_instruction}]

        # Append previous conversation turns (keep last 6 turns to stay lean and fast)
        for turn in self.chat_history[-6:]:
            messages.append(turn)

        messages.append({"role": "user", "content": user_message})

        if stream:
            def stream_and_record():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                assistant_response = "".join(collected)
                self.chat_history.append({"role": "user", "content": user_message})
                self.chat_history.append({"role": "assistant", "content": assistant_response})

            return stream_and_record()
        else:
            response = self.llm.generate(messages)
            self.chat_history.append({"role": "user", "content": user_message})
            self.chat_history.append({"role": "assistant", "content": response})
            return response

    def describe_video(self, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """
        Analyzes the video tutorial and generates a comprehensive, engaging overview
        highlighting core concepts, tech stack, and timestamped milestones.
        """
        self._ensure_loaded()
        if self._description_cache and not stream:
            return self._description_cache

        context = self._build_context()
        prompt = VIDEO_DESCRIPTION_PROMPT.format(
            video_title=self.metadata.get("title", "Tutorial"),
            author_name=self.metadata.get("author_name", "Creator"),
            duration=self.transcript.duration_str
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nTIMESTAMPED TRANSCRIPT REFERENCE:\n{context}"}
        ]

        if stream:
            def stream_and_cache():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                self._description_cache = "".join(collected)

            return stream_and_cache()
        else:
            result = self.llm.generate(messages)
            self._description_cache = result
            return result

    def generate_curriculum(self, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """Generates an organized roadmap/syllabus of the tutorial."""
        self._ensure_loaded()
        if self._curriculum_cache and not stream:
            return self._curriculum_cache

        context = self._build_context()
        prompt = CURRICULUM_PROMPT.format(
            video_title=self.metadata.get("title"),
            author_name=self.metadata.get("author_name"),
            duration=self.transcript.duration_str
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nTIMESTAMPED TRANSCRIPT:\n{context}"}
        ]

        if stream:
            def stream_and_cache():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                self._curriculum_cache = "".join(collected)

            return stream_and_cache()
        else:
            result = self.llm.generate(messages)
            self._curriculum_cache = result
            return result

    def extract_code(self, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """Extracts code snippets, commands, and implementation patterns."""
        self._ensure_loaded()
        if self._code_cache and not stream:
            return self._code_cache

        context = self._build_context()
        prompt = CODE_EXTRACTION_PROMPT.format(
            video_title=self.metadata.get("title")
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nTIMESTAMPED TRANSCRIPT:\n{context}"}
        ]

        if stream:
            def stream_and_cache():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                self._code_cache = "".join(collected)

            return stream_and_cache()
        else:
            result = self.llm.generate(messages)
            self._code_cache = result
            return result

    def generate_study_notes(self, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """Generates cheatsheet and revision notes."""
        self._ensure_loaded()
        if self._notes_cache and not stream:
            return self._notes_cache

        context = self._build_context()
        prompt = STUDY_GUIDE_PROMPT.format(
            video_title=self.metadata.get("title")
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nTIMESTAMPED TRANSCRIPT:\n{context}"}
        ]

        if stream:
            def stream_and_cache():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                self._notes_cache = "".join(collected)

            return stream_and_cache()
        else:
            result = self.llm.generate(messages)
            self._notes_cache = result
            return result

    def generate_quiz(self, stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """Generates mastery quiz and hands-on mini challenge."""
        self._ensure_loaded()
        if self._quiz_cache and not stream:
            return self._quiz_cache

        context = self._build_context()
        prompt = QUIZ_PROMPT.format(
            video_title=self.metadata.get("title")
        )

        messages = [
            {"role": "system", "content": SYSTEM_TUTOR_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nTIMESTAMPED TRANSCRIPT:\n{context}"}
        ]

        if stream:
            def stream_and_cache():
                collected = []
                for chunk in self.llm.generate_stream(messages):
                    collected.append(chunk)
                    yield chunk
                self._quiz_cache = "".join(collected)

            return stream_and_cache()
        else:
            result = self.llm.generate(messages)
            self._quiz_cache = result
            return result

    def search_transcript(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Fast keyword search across video transcript."""
        self._ensure_loaded()
        return self.transcript.search(query, max_results=max_results)

    def fact_check(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Verifies technical claims made in the tutorial using live DuckDuckGo web search
        and the Groq LLM at temperature 0.
        """
        self._ensure_loaded()
        if self._fact_check_cache and not force_refresh:
            return self._fact_check_cache

        from yt_agent.fact_checker import FactCheckAgent
        checker = FactCheckAgent(llm=self.llm, max_searches_per_video=5)

        result = checker.check_video(
            video_id=self.metadata.get("video_id", "video"),
            video_title=self.metadata.get("title", "Tutorial"),
            author_name=self.metadata.get("author_name", "Creator"),
            transcript_text=self.transcript.timestamped_text,
            force_refresh=force_refresh
        )
        self._fact_check_cache = result
        return result

    def export_pdf(self) -> bytes:
        """
        Generates and returns a downloadable PDF report containing the tutorial summary,
        roadmap, quiz, and the live internet Fact Check section.
        """
        self._ensure_loaded()
        from yt_agent.pdf_generator import generate_tutorial_pdf

        # Use cached fact check or run verification
        fact_data = self._fact_check_cache
        if fact_data is None:
            fact_data = self.fact_check()

        return generate_tutorial_pdf(
            metadata=self.get_video_info(),
            description_text=self._description_cache or "",
            curriculum_text=self._curriculum_cache or "",
            fact_check_data=fact_data,
            notes_text=self._notes_cache or "",
            quiz_text=self._quiz_cache or ""
        )

    def annotate_curriculum_with_warnings(self, curriculum_text: str) -> str:
        """
        Optional helper: inspects cached fact check results. If any claim is marked 'outdated',
        prepends or inserts a warning notification for the student.
        """
        if not self._fact_check_cache:
            return curriculum_text

        outdated_claims = [
            c for c in self._fact_check_cache.get("claims", [])
            if c.get("status") == "outdated"
        ]

        if not outdated_claims:
            return curriculum_text

        warning_blocks = ["\n\n> ⚠️ **Fact Check Notice: Potential Outdated Information in this Tutorial**\n> Live web verification detected breaking changes or deprecated syntax:"]
        for oc in outdated_claims:
            ts = f" at `{oc.get('timestamp')}`" if oc.get('timestamp') else ""
            warning_blocks.append(f"> - **Claim{ts}**: {oc.get('claim')}\n>   - *Update*: {oc.get('corrected_info') or oc.get('explanation')}")

        return "\n".join(warning_blocks) + "\n\n" + curriculum_text

    def clear_chat(self):
        """Resets the chat conversation history."""
        self.chat_history = []

