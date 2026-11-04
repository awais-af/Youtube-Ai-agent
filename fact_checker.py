"""
Fact-Checking and Verification Agent for YouTube Tutorials.
Uses DuckDuckGo live web search and Groq LLM to audit technical tutorial claims
for obsolescence, deprecations, and breaking changes.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from yt_agent.web_search import web_search
from yt_agent.llm_provider import LLMProvider, LLMProviderError
from yt_agent.prompts import (
    DECIDE_VERIFICATION_PROMPT,
    CLAIM_EXTRACTION_PROMPT,
    CLAIM_VERIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)

# Global in-memory cache keyed by video_id to avoid redundant searches and save API rate limits
FACT_CHECK_CACHE: Dict[str, Dict[str, Any]] = {}


def _safe_parse_json(text: str, default: Any = None) -> Any:
    """
    Robustly extracts and parses JSON from LLM output, handling markdown fences,
    trailing commas, or prefix commentary.
    """
    if not text:
        return default

    cleaned = text.strip()
    
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Try locating array or object bounds
    try:
        start_obj = cleaned.find("{")
        end_obj = cleaned.rfind("}")
        start_arr = cleaned.find("[")
        end_arr = cleaned.rfind("]")

        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj) and end_arr > start_arr:
            return json.loads(cleaned[start_arr:end_arr + 1])
        elif start_obj != -1 and end_obj > start_obj:
            return json.loads(cleaned[start_obj:end_obj + 1])
    except Exception:
        pass

    logger.warning(f"Failed to safely parse JSON from LLM response: {text[:200]}...")
    return default


class FactCheckAgent:
    """
    Verifies technical claims made in a video tutorial using live web search.
    """

    def __init__(self, llm: LLMProvider, max_searches_per_video: int = 5):
        self.llm = llm
        self.max_searches = max_searches_per_video

    def check_video(
        self,
        video_id: str,
        video_title: str,
        author_name: str,
        transcript_text: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Executes full fact-check pipeline for a tutorial:
        1. Checks video ID cache.
        2. Asks LLM if video requires technical verification.
        3. Extracts 3-5 checkable claims.
        4. Verifies each claim via DuckDuckGo web search + Groq audit.
        5. Caches and returns final structured audit report.
        """
        if not force_refresh and video_id in FACT_CHECK_CACHE:
            logger.info(f"Returning cached fact-check result for video_id={video_id}")
            return FACT_CHECK_CACHE[video_id]

        # 1. Decision Step: Does this video teach perishable technical software/tools?
        # Keep sample concise to save tokens and free-tier TPM
        transcript_sample = transcript_text[:3500] if transcript_text else ""
        decision_messages = [
            {
                "role": "user",
                "content": DECIDE_VERIFICATION_PROMPT.format(
                    video_title=video_title,
                    author_name=author_name,
                    transcript_sample=transcript_sample
                )
            }
        ]

        try:
            decision_raw = self.llm.generate(decision_messages, temperature=0.0, max_tokens=250)
            decision = _safe_parse_json(decision_raw, default={"needs_verification": True, "reason": "Technical tutorial evaluation."})
        except LLMProviderError as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                return {
                    "video_id": video_id,
                    "status": "error",
                    "error": "Groq rate limit reached (429). Please wait a moment before trying again.",
                    "needs_verification": False,
                    "claims": []
                }
            return {
                "video_id": video_id,
                "status": "error",
                "error": f"LLM error during decision step: {str(e)}",
                "needs_verification": False,
                "claims": []
            }
        except Exception as e:
            logger.warning(f"Decision step failed: {e}")
            decision = {"needs_verification": True, "reason": "Proceeding with verification."}

        needs_verification = bool(decision.get("needs_verification", True))
        skip_reason = decision.get("reason", "")

        if not needs_verification:
            result = {
                "video_id": video_id,
                "status": "skipped",
                "needs_verification": False,
                "skip_reason": skip_reason or "Non-technical or conceptual video that does not require live software verification.",
                "claims": []
            }
            FACT_CHECK_CACHE[video_id] = result
            return result

        # 2. Extract 3-5 checkable technical claims
        # Send a compact context window (up to ~7500 chars) to stay safely within Groq TPM limits
        context_slice = transcript_text[:7500] if transcript_text else ""
        extraction_messages = [
            {
                "role": "user",
                "content": CLAIM_EXTRACTION_PROMPT.format(
                    video_title=video_title,
                    transcript_context=context_slice
                )
            }
        ]

        try:
            extraction_raw = self.llm.generate(extraction_messages, temperature=0.0, max_tokens=650)
            raw_claims = _safe_parse_json(extraction_raw, default=[])
        except LLMProviderError as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                return {
                    "video_id": video_id,
                    "status": "error",
                    "error": "Groq rate limit reached (429). Please wait a moment before trying again.",
                    "needs_verification": True,
                    "claims": []
                }
            return {
                "video_id": video_id,
                "status": "error",
                "error": f"LLM claim extraction failed: {str(e)}",
                "needs_verification": True,
                "claims": []
            }
        except Exception as e:
            return {
                "video_id": video_id,
                "status": "error",
                "error": f"Unexpected error during claim extraction: {str(e)}",
                "needs_verification": True,
                "claims": []
            }

        if not isinstance(raw_claims, list) or len(raw_claims) == 0:
            result = {
                "video_id": video_id,
                "status": "success",
                "needs_verification": True,
                "skip_reason": "No perishable technical claims extracted from the transcript.",
                "claims": []
            }
            FACT_CHECK_CACHE[video_id] = result
            return result

        # Cap claims at max_searches (max 5)
        claims_to_check = raw_claims[:self.max_searches]
        verified_claims: List[Dict[str, Any]] = []

        # 3. Verify each claim with DuckDuckGo search + Groq audit
        for item in claims_to_check:
            claim_text = item.get("claim", "").strip()
            search_query = item.get("search_query", claim_text).strip()
            timestamp = item.get("timestamp", "")

            if not claim_text:
                continue

            # Run web search (returns max 3 snippets)
            search_results = web_search(query=search_query, max_results=3)

            # If search results are empty, immediately classify as unverified without guessing
            if not search_results:
                verified_claims.append({
                    "claim": claim_text,
                    "timestamp": timestamp,
                    "search_query": search_query,
                    "status": "unverified",
                    "explanation": "No current search results or documentation found to independently corroborate this claim.",
                    "corrected_info": "",
                    "sources": []
                })
                continue

            # Format snippets for LLM audit
            formatted_snippets = []
            for i, r in enumerate(search_results, 1):
                formatted_snippets.append(
                    f"[{i}] {r.get('title', 'Source')}\nURL: {r.get('url', '')}\nSnippet: {r.get('snippet', '')}"
                )
            snippets_text = "\n\n".join(formatted_snippets)

            verification_messages = [
                {
                    "role": "user",
                    "content": CLAIM_VERIFICATION_PROMPT.format(
                        claim=claim_text,
                        search_results=snippets_text
                    )
                }
            ]

            try:
                verification_raw = self.llm.generate(verification_messages, temperature=0.0, max_tokens=350)
                ver_dict = _safe_parse_json(verification_raw, default={})
                
                status = str(ver_dict.get("status", "unverified")).strip().lower()
                if status not in ["still_valid", "outdated", "unverified"]:
                    status = "unverified"

                explanation = str(ver_dict.get("explanation", "Verification completed.")).strip()
                corrected = str(ver_dict.get("corrected_info", "")).strip()
                sources = ver_dict.get("sources", [])
                
                # If sources missing from LLM output, use the search URLs
                if not sources or not isinstance(sources, list):
                    sources = [r["url"] for r in search_results if r.get("url")]

                verified_claims.append({
                    "claim": claim_text,
                    "timestamp": timestamp,
                    "search_query": search_query,
                    "status": status,
                    "explanation": explanation,
                    "corrected_info": corrected if status == "outdated" else "",
                    "sources": sources[:3]
                })

            except LLMProviderError as e:
                logger.warning(f"LLM verification failed for claim '{claim_text}': {e}")
                verified_claims.append({
                    "claim": claim_text,
                    "timestamp": timestamp,
                    "search_query": search_query,
                    "status": "unverified",
                    "explanation": f"LLM rate limit or verification error: {str(e)}",
                    "corrected_info": "",
                    "sources": [r["url"] for r in search_results if r.get("url")]
                })
            except Exception as e:
                logger.warning(f"Unexpected error verifying claim '{claim_text}': {e}")
                verified_claims.append({
                    "claim": claim_text,
                    "timestamp": timestamp,
                    "search_query": search_query,
                    "status": "unverified",
                    "explanation": "Unable to verify claim due to an unexpected evaluation error.",
                    "corrected_info": "",
                    "sources": [r["url"] for r in search_results if r.get("url")]
                })

        final_result = {
            "video_id": video_id,
            "status": "success",
            "needs_verification": True,
            "total_claims": len(verified_claims),
            "claims": verified_claims
        }

        # Cache result
        FACT_CHECK_CACHE[video_id] = final_result
        return final_result
