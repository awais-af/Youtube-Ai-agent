"""
YouTube Tutorial AI Agent - Flask Web Server.
Exposes REST and SSE streaming endpoints for video ingestion, description, and AI tutor Q&A.
"""

import os
import io
import json
from typing import Dict
from flask import Flask, request, jsonify, render_template, Response, stream_with_context, send_file
from dotenv import load_dotenv

from yt_agent.agent import YouTubeTutorialAgent
from yt_agent.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    DEFAULT_PROVIDER,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
)
from yt_agent.extractor import YouTubeExtractorError, TranscriptUnavailableError, InvalidYouTubeURLError

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

# In-memory cache of loaded agents by video_id or session
agent_cache: Dict[str, YouTubeTutorialAgent] = {}


def get_or_create_agent(url: str, provider: str = "groq", api_key: str = None, model: str = None) -> YouTubeTutorialAgent:
    """Helper to fetch or instantiate an agent loaded with the video."""
    resolved_key = api_key
    if not resolved_key or resolved_key == "ENV_KEY_LOADED":
        resolved_key = GROQ_API_KEY if provider == "groq" else OPENAI_API_KEY

    cache_key = f"{url}_{provider}_{model}"
    if cache_key in agent_cache:
        agent = agent_cache[cache_key]
        if resolved_key and agent.llm.api_key != resolved_key:
            agent.llm.switch_provider(provider, api_key=resolved_key, model=model)
        return agent

    agent = YouTubeTutorialAgent(provider=provider, api_key=resolved_key, model=model)
    agent.load_video(url)
    agent_cache[cache_key] = agent
    return agent


@app.route("/")
def index():
    """Renders the main web interface."""
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Returns current environment configurations."""
    has_groq = bool(os.getenv("GROQ_API_KEY", "").strip())
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return jsonify({
        "default_provider": DEFAULT_PROVIDER,
        "default_groq_model": DEFAULT_GROQ_MODEL,
        "default_openai_model": DEFAULT_OPENAI_MODEL,
        "has_env_key": has_groq or has_openai,
        "env_key_placeholder": "ENV_KEY_LOADED" if (has_groq or has_openai) else "",
    })


@app.route("/api/analyze", methods=["POST"])
def analyze_video():
    """
    Ingests video, extracts metadata and transcript,
    and generates an in-depth tutorial description.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    provider = data.get("provider", "groq").strip().lower()
    api_key = data.get("api_key", "").strip()
    model = data.get("model")

    if not url:
        return jsonify({"error": "No YouTube video URL provided."}), 400

    try:
        agent = get_or_create_agent(url=url, provider=provider, api_key=api_key, model=model)
        metadata = agent.get_video_info()

        # Generate agent description
        description = agent.describe_video()

        return jsonify({
            "status": "success",
            "metadata": metadata,
            "description": description
        })

    except InvalidYouTubeURLError as e:
        return jsonify({"error": f"Invalid YouTube link: {str(e)}"}), 400
    except TranscriptUnavailableError as e:
        return jsonify({"error": f"Subtitles/Transcript not available: {str(e)}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Interactive Q&A endpoint streaming responses token-by-token
    using Server-Sent Events (SSE).
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    question = data.get("question", "").strip()
    provider = data.get("provider", "groq").strip().lower()
    api_key = data.get("api_key", "").strip()
    model = data.get("model")
    history = data.get("chat_history", [])

    if not url or not question:
        return jsonify({"error": "Missing URL or question."}), 400

    try:
        agent = get_or_create_agent(url=url, provider=provider, api_key=api_key, model=model)

        # Sync history if provided
        if history:
            agent.chat_history = history

        def generate_events():
            try:
                for chunk in agent.chat(question, stream=True):
                    # Replace actual newlines with escaped \n for SSE format
                    escaped_chunk = chunk.replace("\n", "\\n")
                    yield f"data: {escaped_chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as stream_err:
                err_msg = str(stream_err).replace("\n", " ")
                yield f"data: ⚠️ Error: {err_msg}\n\n"
                yield "data: [DONE]\n\n"

        return Response(stream_with_context(generate_events()), mimetype="text/event-stream")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/action", methods=["POST"])
def handle_action():
    """
    Generates specialized reports: code, notes, or quiz.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    action = data.get("action", "").strip().lower()
    provider = data.get("provider", "groq").strip().lower()
    api_key = data.get("api_key", "").strip()
    model = data.get("model")

    if not url or not action:
        return jsonify({"error": "Missing URL or action parameter."}), 400

    try:
        agent = get_or_create_agent(url=url, provider=provider, api_key=api_key, model=model)

        if action == "code":
            content = agent.extract_code()
        elif action == "notes":
            content = agent.generate_study_notes()
        elif action == "quiz":
            content = agent.generate_quiz()
        elif action == "curriculum":
            content = agent.generate_curriculum()
        elif action in ["fact_check", "factcheck"]:
            content = agent.fact_check()
            return jsonify({"status": "success", "action": action, "data": content})
        else:
            return jsonify({"error": f"Unknown action: '{action}'"}), 400

        return jsonify({"status": "success", "action": action, "content": content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fact-check", methods=["POST"])
@app.route("/fact-check", methods=["POST"])
def fact_check_endpoint():
    """
    Internet Search Fact-Checking endpoint.
    Accepts video URL or video ID and returns extracted claims,
    status (still_valid / outdated / unverified), explanations, and sources.
    """
    data = request.get_json() or {}
    url = data.get("url") or data.get("video_url") or data.get("video_id") or ""
    url = str(url).strip()
    provider = data.get("provider", "groq").strip().lower()
    api_key = data.get("api_key", "").strip()
    model = data.get("model")
    force_refresh = bool(data.get("refresh", False))

    if not url:
        return jsonify({"error": "Missing 'url' or 'video_id' parameter."}), 400

    try:
        agent = get_or_create_agent(url=url, provider=provider, api_key=api_key, model=model)
        result = agent.fact_check(force_refresh=force_refresh)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/api/download-pdf", methods=["POST"])
@app.route("/download-pdf", methods=["POST"])
def download_pdf_endpoint():
    """
    Generates and downloads a comprehensive PDF report including description,
    roadmap, quiz, and the live internet Fact Check section.
    """
    data = request.get_json() or {}
    url = data.get("url") or data.get("video_url") or data.get("video_id") or ""
    url = str(url).strip()
    provider = data.get("provider", "groq").strip().lower()
    api_key = data.get("api_key", "").strip()
    model = data.get("model")

    if not url:
        return jsonify({"error": "Missing 'url' or 'video_id' parameter."}), 400

    try:
        agent = get_or_create_agent(url=url, provider=provider, api_key=api_key, model=model)
        pdf_bytes = agent.export_pdf()
        video_id = agent.metadata.get("video_id", "tutorial")
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"tutorial_report_{video_id}.pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Awais(YT) Ai Agent Web Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


