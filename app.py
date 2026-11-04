"""
YouTube Tutorial AI Agent - Streamlit Web Application.
Interactive UI for extracting insights, code, study guides, and timestamped Q&A from YouTube tutorials.
"""

import os
import streamlit as st
from yt_agent.agent import YouTubeTutorialAgent
from yt_agent.extractor import YouTubeExtractorError, TranscriptUnavailableError, InvalidYouTubeURLError
from yt_agent.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    AVAILABLE_GROQ_MODELS,
    AVAILABLE_OPENAI_MODELS,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
)

# Page configuration
st.set_page_config(
    page_title="Awais(YT) Ai Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Modern Dark Glassmorphism Aesthetic)
st.markdown("""
<style>
    /* Global Theme Overrides */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Header Container */
    .hero-container {
        padding: 1.5rem 2rem;
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        backdrop-filter: blur(12px);
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-sub {
        color: #94a3b8;
        font-size: 1.05rem;
    }

    /* Video Metadata Card */
    .video-card {
        background: rgba(30, 41, 59, 0.6);
        border-left: 4px solid #6366f1;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
        display: flex;
        gap: 1.2rem;
        align-items: center;
    }
    .video-thumb {
        border-radius: 8px;
        width: 140px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.25);
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.4);
        margin-right: 0.4rem;
    }

    /* Metric Badges */
    .metric-chip {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        text-align: center;
    }
    .metric-val {
        font-size: 1.2rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Timestamp tag formatting */
    .timestamp-tag {
        background-color: #312e81;
        color: #a5b4fc;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "agent" not in st.session_state:
    st.session_state.agent = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "video_loaded" not in st.session_state:
    st.session_state.video_loaded = False
if "description_text" not in st.session_state:
    st.session_state.description_text = ""
if "curriculum_text" not in st.session_state:
    st.session_state.curriculum_text = ""
if "code_text" not in st.session_state:
    st.session_state.code_text = ""
if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""
if "quiz_text" not in st.session_state:
    st.session_state.quiz_text = ""
if "fact_check_data" not in st.session_state:
    st.session_state.fact_check_data = None


# Sidebar: LLM Provider Configuration
with st.sidebar:
    st.markdown("### ⚙️ LLM Agent Settings")

    provider = st.radio(
        "Select Provider",
        options=["Groq", "OpenAI"],
        index=0,
        help="Groq offers ultra-fast inference with Llama-3.3 70B. OpenAI offers GPT-4o models."
    ).lower()

    if provider == "groq":
        env_key = GROQ_API_KEY
        key_label = "Groq API Key"
        key_help = "Get a free key from console.groq.com"
        default_model = DEFAULT_GROQ_MODEL
        model_options = AVAILABLE_GROQ_MODELS
    else:
        env_key = OPENAI_API_KEY
        key_label = "OpenAI API Key"
        key_help = "Get a key from platform.openai.com"
        default_model = DEFAULT_OPENAI_MODEL
        model_options = AVAILABLE_OPENAI_MODELS

    api_key_input = st.text_input(
        key_label,
        value=env_key,
        type="password",
        help=key_help
    )

    selected_model = st.selectbox(
        "Model",
        options=model_options,
        index=0
    )

    if not api_key_input:
        st.warning(f"⚠️ Please enter your {provider.capitalize()} API Key to start tutoring.")
    else:
        st.success(f"✅ {provider.capitalize()} Key Ready")

    st.markdown("---")

    # Sample Video Prompts for easy one-click testing
    st.markdown("### 💡 Quick Sample Tutorials")
    samples = {
        "Python for Beginners (Mosh)": "https://www.youtube.com/watch?v=kqtD5dpn9C8",
        "LangChain in 1 Hour": "https://www.youtube.com/watch?v=yF9kGESA354",
        "FastAPI Full Course": "https://www.youtube.com/watch?v=0sOvCWFmrtA",
    }
    for title, url in samples.items():
        if st.button(title, use_container_width=True):
            st.session_state.sample_url = url

    st.markdown("---")
    st.caption("Awais(YT) Ai Agent | Powered by Groq & OpenAI")


# Main Page Header
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🎬 Awais(YT) Ai Agent</div>
    <div class="hero-sub">
        Transform any video tutorial into an interactive personal coding tutor. Paste a link to get an automatic in-depth description, then ask any question—the agent replies using both tutorial knowledge and its own intelligence.
    </div>
</div>
""", unsafe_allow_html=True)


# Video Input Bar
default_input_val = st.session_state.get("sample_url", "")
col_input, col_btn = st.columns([4, 1])

with col_input:
    youtube_url = st.text_input(
        "YouTube Video Link",
        value=default_input_val,
        placeholder="Paste any YouTube video URL (e.g. https://www.youtube.com/watch?v=kqtD5dpn9C8)",
        label_visibility="collapsed"
    )

with col_btn:
    analyze_btn = st.button("🚀 Analyze Video", type="primary", use_container_width=True)


# Action: Ingest Video
if analyze_btn:
    if not youtube_url:
        st.error("Please enter a valid YouTube video link.")
    elif not api_key_input:
        st.error(f"Please provide your {provider.capitalize()} API Key in the sidebar.")
    else:
        with st.spinner("🔍 Fetching metadata, transcript & generating agent description..."):
            try:
                agent = YouTubeTutorialAgent(
                    provider=provider,
                    api_key=api_key_input,
                    model=selected_model
                )
                info = agent.load_video(youtube_url)

                st.session_state.agent = agent
                st.session_state.video_loaded = True
                st.session_state.video_info = info
                st.session_state.messages = []
                st.session_state.description_text = agent.describe_video()
                st.session_state.curriculum_text = ""
                st.session_state.code_text = ""
                st.session_state.notes_text = ""
                st.session_state.quiz_text = ""
                st.session_state.fact_check_data = None

                st.toast("🎉 Tutorial successfully analyzed and described!", icon="✅")
            except InvalidYouTubeURLError as e:
                st.error(f"❌ Invalid YouTube URL: {str(e)}")
            except TranscriptUnavailableError as e:
                st.error(f"⚠️ Transcript unavailable: {str(e)}\nMake sure the video has closed captions/subtitles enabled.")
            except Exception as e:
                st.error(f"❌ Failed to load video: {str(e)}")


# Display Active Video Dashboard if loaded
if st.session_state.video_loaded and st.session_state.agent:
    agent: YouTubeTutorialAgent = st.session_state.agent
    
    # Update provider/model if changed in sidebar
    if (agent.provider_name != provider or agent.llm.model != selected_model or agent.llm.api_key != api_key_input):
        try:
            agent.switch_provider(provider=provider, api_key=api_key_input, model=selected_model)
        except Exception as e:
            st.error(f"Error updating provider: {e}")

    info = st.session_state.get("video_info", agent.get_video_info())

    # Metadata & Quick Stats Bar
    col_card, col_m1, col_m2, col_m3, col_m4 = st.columns([3, 1, 1, 1, 1])

    with col_card:
        st.markdown(f"""
        <div style="display: flex; gap: 15px; align-items: center; background: rgba(30, 41, 59, 0.4); padding: 10px 14px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
            <img src="{info.get('thumbnail_url')}" style="width: 100px; border-radius: 8px; object-fit: cover;" />
            <div>
                <div style="font-weight: 700; font-size: 1.05rem; line-height: 1.3;">{info.get('title')}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">📺 {info.get('author_name')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_m1:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-val">{info.get('duration')}</div>
            <div class="metric-lbl">Duration</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m2:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-val">{info.get('total_segments', 0):,}</div>
            <div class="metric-lbl">Captions</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m3:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-val">{info.get('total_words', 0):,}</div>
            <div class="metric-lbl">Words</div>
        </div>
        """, unsafe_allow_html=True)

    with col_m4:
        st.markdown(f"""
        <div class="metric-chip">
            <div class="metric-val">{info.get('total_blocks', 0)}</div>
            <div class="metric-lbl">Modules</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Collapsible video player
    with st.expander("▶️ Watch Video Player", expanded=False):
        st.video(info.get("video_url"))

    # Seven Navigation Tabs
    tab_chat, tab_factcheck, tab_curriculum, tab_code, tab_notes, tab_quiz, tab_transcript = st.tabs([
        "💬 Interactive Tutor (Q&A)",
        "🔍 Live Fact Check",
        "🗺️ Step-by-Step Roadmap",
        "💻 Code & Commands Extractor",
        "📝 Study Guide & Cheatsheet",
        "🧠 Mastery Quiz & Challenge",
        "📜 Searchable Transcript"
    ])

    # -------------------------------------------------------------
    # TAB 1: INTERACTIVE TUTOR (Q&A & CHAT)
    # -------------------------------------------------------------
    with tab_chat:
        # Agent's In-Depth Video Description
        if st.session_state.description_text:
            with st.expander("📑 Agent's Video Description & Breakdown", expanded=True):
                st.markdown(st.session_state.description_text)
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button(
                        "📥 Download Overview (.md)",
                        data=st.session_state.description_text,
                        file_name=f"overview_{info.get('video_id')}.md",
                        mime="text/markdown",
                        key="dl_desc_btn"
                    )
                with c_dl2:
                    if st.button("📥 Export Tutorial PDF", key="export_pdf_desc"):
                        with st.spinner("Generating PDF with Fact Check report..."):
                            pdf_data = agent.export_pdf()
                            st.download_button(
                                "⬇️ Download PDF Report",
                                data=pdf_data,
                                file_name=f"tutorial_{info.get('video_id')}.pdf",
                                mime="application/pdf",
                                key="pdf_dl_desc_btn"
                            )

        st.markdown("#### 💬 Ask the AI Tutor")
        st.caption("Ask questions about the tutorial. The agent replies using both the video's contents and its own AI intelligence.")

        # Quick Question Buttons
        c1, c2, c3, c4 = st.columns(4)
        quick_query = None
        if c1.button("📌 Explain Core Concept", use_container_width=True):
            quick_query = "What is the core concept explained in this tutorial and why is it important?"
        if c2.button("🛠️ Tech Stack & Prerequisites", use_container_width=True):
            quick_query = "What tools, libraries, and prerequisites are required to follow this tutorial?"
        if c3.button("⚠️ Common Pitfalls & Mistakes", use_container_width=True):
            quick_query = "What common mistakes, pitfalls, or edge cases did the speaker warn about?"
        if c4.button("⚡ Summary of Steps", use_container_width=True):
            quick_query = "Can you provide a chronological summary of each step demonstrated in the video with timestamps?"

        # Display Chat History
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Process Quick Query if clicked
        user_prompt = quick_query or st.chat_input("Ask a question about this tutorial (e.g. 'How does step 2 work?')...")

        if user_prompt:
            # Display user message
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # Generate Agent Response
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                stream_generator = agent.chat(user_prompt, stream=True)
                full_response = ""
                try:
                    for chunk in stream_generator:
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"Error generating answer: {str(e)}")

        if st.session_state.messages:
            if st.button("🧹 Clear Chat History"):
                st.session_state.messages = []
                agent.clear_chat()
                st.rerun()

    # -------------------------------------------------------------
    # TAB 2: LIVE INTERNET FACT CHECK (DUCKDUCKGO + GROQ)
    # -------------------------------------------------------------
    with tab_factcheck:
        st.markdown("#### 🔍 Live Internet Fact Check")
        st.caption("Verifies technical claims, package commands, and syntax against live DuckDuckGo web search via Groq AI.")

        col_fc_btn, col_fc_dl = st.columns([2, 3])
        with col_fc_btn:
            run_fc_btn = st.button("🔄 Audit Technical Claims", type="primary")

        if run_fc_btn:
            with st.spinner("Auditing claims with live DuckDuckGo search & Groq AI..."):
                try:
                    fc_result = agent.fact_check(force_refresh=True)
                    st.session_state.fact_check_data = fc_result
                    st.toast("Fact check audit complete!", icon="✅")
                except Exception as e:
                    st.error(f"Error during fact check: {e}")

        # Render Fact Check UI if data available
        fc_data = st.session_state.fact_check_data or (agent._fact_check_cache)
        if fc_data:
            if not fc_data.get("needs_verification"):
                st.info(f"ℹ️ **Verification Skipped**: {fc_data.get('skip_reason', 'Non-technical video.')}")
            elif fc_data.get("status") == "error":
                st.error(f"⚠️ {fc_data.get('error', 'Fact checking service error.')}")
            else:
                claims = fc_data.get("claims", [])
                if not claims:
                    st.info("No perishable technical commands or version claims were detected in this transcript.")
                else:
                    st.markdown(f"**Audited {len(claims)} technical claims against live web documentation:**")
                    for idx, item in enumerate(claims, 1):
                        status = item.get("status", "unverified")
                        ts = f"⏱️ `{item.get('timestamp')}`" if item.get("timestamp") else ""
                        
                        if status == "still_valid":
                            badge = "✅ **STILL VALID**"
                            card_bg = "rgba(16, 185, 129, 0.1)"
                            border = "1px solid rgba(16, 185, 129, 0.4)"
                        elif status == "outdated":
                            badge = "⚠️ **OUTDATED - CHANGES DETECTED**"
                            card_bg = "rgba(245, 158, 11, 0.12)"
                            border = "1px solid rgba(245, 158, 11, 0.5)"
                        else:
                            badge = "❓ **UNVERIFIED**"
                            card_bg = "rgba(148, 163, 184, 0.1)"
                            border = "1px solid rgba(148, 163, 184, 0.3)"

                        st.markdown(f"""
                        <div style="background: {card_bg}; border: {border}; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-weight: 700; color: #94a3b8; font-size: 0.85rem;">CLAIM #{idx} &nbsp; {ts}</span>
                                <span style="font-size: 0.85rem;">{badge}</span>
                            </div>
                            <div style="font-weight: 600; font-size: 1.0rem; color: #f8fafc; margin-bottom: 8px;">
                                "{item.get('claim')}"
                            </div>
                            <div style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5;">
                                {item.get('explanation')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if status == "outdated" and item.get("corrected_info"):
                            st.warning(f"⚡ **Modern Replacement / Fix**: {item.get('corrected_info')}")

                        sources = item.get("sources", [])
                        if sources:
                            src_links = " • ".join([f"[{s}]({s})" for s in sources[:2]])
                            st.caption(f"Sources: {src_links}")
                        st.markdown("---")

                    with col_fc_dl:
                        if st.button("📥 Download Tutorial Report (PDF)"):
                            with st.spinner("Generating PDF report..."):
                                pdf_bytes = agent.export_pdf()
                                st.download_button(
                                    "⬇️ Save PDF File",
                                    data=pdf_bytes,
                                    file_name=f"tutorial_report_{info.get('video_id')}.pdf",
                                    mime="application/pdf",
                                    key="save_fc_pdf_btn"
                                )
        else:
            st.info("Click **'Audit Technical Claims'** above to verify code, installation commands, and APIs taught in this tutorial against live DuckDuckGo web search.")

    # -------------------------------------------------------------
    # TAB 3: STEP-BY-STEP ROADMAP & SYLLABUS
    # -------------------------------------------------------------
    with tab_curriculum:
        st.markdown("#### 🗺️ Tutorial Roadmap & Syllabus")
        st.caption("Chronological module-by-module breakdown with exact timestamps and learning goals.")

        # Check if outdated claims exist and warn
        if st.session_state.fact_check_data and st.session_state.fact_check_data.get("claims"):
            outdated = [c for c in st.session_state.fact_check_data["claims"] if c.get("status") == "outdated"]
            if outdated:
                st.warning(f"⚠️ **Fact Check Notice**: {len(outdated)} technical claim(s) in this tutorial were detected as outdated by web search. See the 'Live Fact Check' tab for modern syntax.")

        col_act, _ = st.columns([2, 5])
        with col_act:
            gen_curr_btn = st.button("🔄 Generate / Refresh Roadmap", type="secondary")

        if gen_curr_btn or not st.session_state.curriculum_text:
            with st.spinner("Building step-by-step tutorial syllabus..."):
                try:
                    curr_stream = agent.generate_curriculum(stream=True)
                    placeholder = st.empty()
                    accumulated = ""
                    for chunk in curr_stream:
                        accumulated += chunk
                        placeholder.markdown(accumulated + "▌")
                    placeholder.markdown(accumulated)
                    st.session_state.curriculum_text = accumulated
                except Exception as e:
                    st.error(f"Error generating syllabus: {str(e)}")
        else:
            st.markdown(st.session_state.curriculum_text)

        if st.session_state.curriculum_text:
            st.download_button(
                "📥 Download Syllabus (.md)",
                data=st.session_state.curriculum_text,
                file_name=f"roadmap_{info.get('video_id')}.md",
                mime="text/markdown"
            )

    # -------------------------------------------------------------
    # TAB 3: CODE & COMMANDS EXTRACTOR
    # -------------------------------------------------------------
    with tab_code:
        st.markdown("#### 💻 Extracted Code, Commands & Implementation")
        st.caption("Reconstructed code scripts, terminal commands, configurations, and syntax from the video.")

        col_act, _ = st.columns([2, 5])
        with col_act:
            gen_code_btn = st.button("🔄 Extract Code Snippets", type="secondary")

        if gen_code_btn or not st.session_state.code_text:
            with st.spinner("Extracting all runnable code and commands..."):
                try:
                    code_stream = agent.extract_code(stream=True)
                    placeholder = st.empty()
                    accumulated = ""
                    for chunk in code_stream:
                        accumulated += chunk
                        placeholder.markdown(accumulated + "▌")
                    placeholder.markdown(accumulated)
                    st.session_state.code_text = accumulated
                except Exception as e:
                    st.error(f"Error extracting code: {str(e)}")
        else:
            st.markdown(st.session_state.code_text)

        if st.session_state.code_text:
            st.download_button(
                "📥 Download Code Guide (.md)",
                data=st.session_state.code_text,
                file_name=f"code_guide_{info.get('video_id')}.md",
                mime="text/markdown"
            )

    # -------------------------------------------------------------
    # TAB 4: STUDY GUIDE & CHEATSHEET
    # -------------------------------------------------------------
    with tab_notes:
        st.markdown("#### 📝 Study Guide & Cheatsheet")
        st.caption("Key definitions, quick reference cheatsheet, FAQ, and 3-minute flashcards.")

        col_act, _ = st.columns([2, 5])
        with col_act:
            gen_notes_btn = st.button("🔄 Generate Study Guide", type="secondary")

        if gen_notes_btn or not st.session_state.notes_text:
            with st.spinner("Synthesizing comprehensive study guide..."):
                try:
                    notes_stream = agent.generate_study_notes(stream=True)
                    placeholder = st.empty()
                    accumulated = ""
                    for chunk in notes_stream:
                        accumulated += chunk
                        placeholder.markdown(accumulated + "▌")
                    placeholder.markdown(accumulated)
                    st.session_state.notes_text = accumulated
                except Exception as e:
                    st.error(f"Error generating notes: {str(e)}")
        else:
            st.markdown(st.session_state.notes_text)

        if st.session_state.notes_text:
            st.download_button(
                "📥 Download Study Notes (.md)",
                data=st.session_state.notes_text,
                file_name=f"study_notes_{info.get('video_id')}.md",
                mime="text/markdown"
            )

    # -------------------------------------------------------------
    # TAB 5: MASTERY QUIZ & PRACTICE CHALLENGE
    # -------------------------------------------------------------
    with tab_quiz:
        st.markdown("#### 🧠 Tutorial Comprehension Quiz & Hands-on Challenge")
        st.caption("Test your retention with multiple-choice questions and a practical coding challenge.")

        col_act, _ = st.columns([2, 5])
        with col_act:
            gen_quiz_btn = st.button("🔄 Generate Practice Quiz", type="secondary")

        if gen_quiz_btn or not st.session_state.quiz_text:
            with st.spinner("Generating quiz questions and challenges from video content..."):
                try:
                    quiz_stream = agent.generate_quiz(stream=True)
                    placeholder = st.empty()
                    accumulated = ""
                    for chunk in quiz_stream:
                        accumulated += chunk
                        placeholder.markdown(accumulated + "▌")
                    placeholder.markdown(accumulated)
                    st.session_state.quiz_text = accumulated
                except Exception as e:
                    st.error(f"Error generating quiz: {str(e)}")
        else:
            st.markdown(st.session_state.quiz_text)

    # -------------------------------------------------------------
    # TAB 6: SEARCHABLE TRANSCRIPT
    # -------------------------------------------------------------
    with tab_transcript:
        st.markdown("#### 📜 Searchable Timestamped Transcript")
        st.caption("Search for specific topics or keywords in the video transcript.")

        search_query = st.text_input("Search Transcript", placeholder="e.g. function, loop, import, API...")
        if search_query:
            results = agent.search_transcript(search_query, max_results=8)
            st.markdown(f"**Found {len(results)} matching moments:**")
            for res in results:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.5); border-left: 3px solid #38bdf8; padding: 8px 12px; margin-bottom: 8px; border-radius: 6px;">
                    <span class="timestamp-tag">⏱️ {res['timestamp']} - {res['end_timestamp']}</span>
                    <p style="margin-top: 6px; color: #e2e8f0; font-size: 0.95rem;">{res['text']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.expander("📄 View Full Raw Transcript (with timestamps)", expanded=False):
                st.text_area(
                    "Transcript Text",
                    value=agent.transcript.timestamped_text,
                    height=450,
                    label_visibility="collapsed"
                )

else:
    # Landing Guide when no video is loaded
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 2rem; text-align: center; margin-top: 2rem;">
        <h3 style="color: #a5b4fc; margin-bottom: 0.5rem;">Ready to Learn from Any YouTube Tutorial?</h3>
        <p style="color: #94a3b8; max-width: 600px; margin: 0 auto 1.5rem auto;">
            Enter a YouTube URL above and click <b>"Analyze Video"</b>. You can also pick one of the sample tutorials from the sidebar to see how the agent breaks down tutorials into code, syllabus, and timestamped Q&A.
        </p>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="text-align: left; max-width: 200px;">
                <div style="font-size: 1.5rem;">⏱️</div>
                <b>Timestamp Citations</b>
                <p style="font-size: 0.85rem; color: #94a3b8;">Jump straight to the exact second in the video where topics are taught.</p>
            </div>
            <div style="text-align: left; max-width: 200px;">
                <div style="font-size: 1.5rem;">💻</div>
                <b>Code Extraction</b>
                <p style="font-size: 0.85rem; color: #94a3b8;">Get clean, runnable code, configurations, and terminal commands.</p>
            </div>
            <div style="text-align: left; max-width: 200px;">
                <div style="font-size: 1.5rem;">🧠</div>
                <b>Active Recall</b>
                <p style="font-size: 0.85rem; color: #94a3b8;">Reinforce your understanding with auto-generated quizzes and challenges.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
