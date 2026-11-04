"""
Transcript Processor.
Formats, chunks, and structures YouTube transcripts with timestamps for LLM consumption.
"""

from typing import List, Dict, Any, Tuple
import math


def format_timestamp(seconds: float) -> str:
    """Converts seconds into HH:MM:SS or MM:SS format."""
    total_seconds = int(max(0, math.floor(seconds)))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class ProcessedTranscript:
    """Represents an enriched, structured YouTube transcript."""

    def __init__(self, raw_segments: List[Dict[str, Any]], interval_seconds: int = 90):
        self.raw_segments = raw_segments
        self.interval_seconds = interval_seconds
        
        self.duration_seconds = 0.0
        if raw_segments:
            last = raw_segments[-1]
            self.duration_seconds = float(last.get("start", 0)) + float(last.get("duration", 0))

        self.duration_str = format_timestamp(self.duration_seconds)
        self.total_segments = len(raw_segments)
        
        # Build representations
        self.full_text = " ".join([seg.get("text", "").strip() for seg in raw_segments if seg.get("text")])
        self.timestamped_text = self._build_timestamped_text()
        self.chunks = self._build_chunks()

    def _build_timestamped_text(self) -> str:
        """
        Groups transcript snippets into blocks tagged with [MM:SS] timestamps.
        Each block represents ~60-90 seconds of speech.
        """
        if not self.raw_segments:
            return ""

        blocks: List[str] = []
        current_block_texts: List[str] = []
        current_block_start = None

        for seg in self.raw_segments:
            start = float(seg.get("start", 0))
            text = seg.get("text", "").strip()
            if not text:
                continue

            if current_block_start is None:
                current_block_start = start

            # If time has exceeded the interval, flush current block first
            if (start - current_block_start >= self.interval_seconds) and current_block_texts:
                timestamp_tag = f"[{format_timestamp(current_block_start)}]"
                combined_text = " ".join(current_block_texts)
                blocks.append(f"{timestamp_tag} {combined_text}")
                current_block_texts = []
                current_block_start = start

            current_block_texts.append(text)

        # Flush any remaining items
        if current_block_texts and current_block_start is not None:
            timestamp_tag = f"[{format_timestamp(current_block_start)}]"
            combined_text = " ".join(current_block_texts)
            blocks.append(f"{timestamp_tag} {combined_text}")

        return "\n\n".join(blocks)

    def _build_chunks(self) -> List[Dict[str, Any]]:
        """Splits transcript into structured chunks suitable for retrieval or inspection."""
        if not self.raw_segments:
            return []

        chunks = []
        current_texts: List[str] = []
        chunk_start = None
        last_seg_end = 0.0

        for seg in self.raw_segments:
            start = float(seg.get("start", 0))
            duration = float(seg.get("duration", 0))
            text = seg.get("text", "").strip()
            if not text:
                continue

            if chunk_start is None:
                chunk_start = start

            # Flush previous chunk if elapsed time exceeds interval
            if (start - chunk_start >= self.interval_seconds) and current_texts:
                chunk_text = " ".join(current_texts)
                chunks.append({
                    "start": chunk_start,
                    "end": last_seg_end,
                    "timestamp": format_timestamp(chunk_start),
                    "end_timestamp": format_timestamp(last_seg_end),
                    "text": chunk_text,
                    "word_count": len(chunk_text.split()),
                })
                current_texts = []
                chunk_start = start

            current_texts.append(text)
            last_seg_end = start + duration

        if current_texts and chunk_start is not None:
            chunk_text = " ".join(current_texts)
            chunks.append({
                "start": chunk_start,
                "end": last_seg_end,
                "timestamp": format_timestamp(chunk_start),
                "end_timestamp": format_timestamp(last_seg_end),
                "text": chunk_text,
                "word_count": len(chunk_text.split()),
            })

        return chunks

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Searches transcript segments for matching words/phrases.
        Returns matching segments with timestamps.
        """
        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk in self.chunks:
            chunk_lower = chunk["text"].lower()
            matches = sum(1 for word in query_words if word in chunk_lower)
            if matches > 0:
                scored_chunks.append((matches, chunk))

        # Sort by match count descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:max_results]]

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns statistics about the transcript."""
        return {
            "duration": self.duration_str,
            "duration_seconds": self.duration_seconds,
            "total_segments": self.total_segments,
            "total_words": len(self.full_text.split()),
            "total_blocks": len(self.chunks)
        }
