"""
DuckDuckGo Web Search Tool.
Provides a resilient, retry-enabled search function using the ddgs package
with zero API keys required.
"""

import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 3, timeout: int = 8, retries: int = 2) -> List[Dict[str, str]]:
    """
    Performs a live web search using DuckDuckGo (via the ddgs package).
    
    Args:
        query: Search term or question.
        max_results: Maximum number of search snippets to return (default 3).
        timeout: Request timeout in seconds.
        retries: Number of retry attempts on failure (default 2).

    Returns:
        List of dicts: [{"title": ..., "url": ..., "snippet": ...}]
        Returns [] if search fails, times out, or encounters errors (never crashes).
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    # Attempt import of ddgs (or fallback duckduckgo_search)
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        logger.error("ddgs package is not installed. Run 'pip install ddgs'.")
        return []

    last_error = None
    for attempt in range(retries + 1):
        try:
            with DDGS(timeout=timeout) as ddgs:
                raw_results = list(ddgs.text(clean_query, max_results=max_results))
                
                formatted_results: List[Dict[str, str]] = []
                for item in raw_results:
                    title = str(item.get("title", "")).strip()
                    url = str(item.get("href", item.get("url", ""))).strip()
                    # Truncate snippet to 350 chars to avoid prompt bloat and keep context safe
                    body = str(item.get("body", item.get("snippet", ""))).strip()[:350]
                    
                    if url and (title or body):
                        formatted_results.append({
                            "title": title,
                            "url": url,
                            "snippet": body
                        })

                return formatted_results

        except Exception as e:
            last_error = e
            logger.warning(f"DuckDuckGo search attempt {attempt + 1} failed for query '{clean_query}': {e}")
            if attempt < retries:
                time.sleep(1.2 * (attempt + 1))  # Backoff before retrying

    logger.error(f"DuckDuckGo search failed after {retries + 1} attempts for query '{clean_query}': {last_error}")
    return []
