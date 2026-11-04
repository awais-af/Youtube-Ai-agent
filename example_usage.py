"""
Example Usage of YouTube Tutorial AI Agent in Python.
Demonstrates how to use the agent programmatically inside Python workflows.
"""

import os
from dotenv import load_dotenv
from yt_agent import YouTubeTutorialAgent

load_dotenv()


def main():
    # 1. Initialize Agent with Groq (or OpenAI)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("Note: Set GROQ_API_KEY in .env to run live LLM completions.")
        print("Continuing with video metadata & transcript extraction demo...\n")

    agent = YouTubeTutorialAgent(
        provider="groq",
        api_key=groq_api_key or "dummy_key_for_extraction_test",
        model="llama-3.3-70b-versatile"
    )

    # 2. Ingest any YouTube Tutorial URL
    tutorial_url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"  # Python for Beginners
    print(f"Loading tutorial: {tutorial_url}...")
    
    info = agent.load_video(tutorial_url)
    print("\n--- Tutorial Info ---")
    print(f"Title:        {info['title']}")
    print(f"Author:       {info['author_name']}")
    print(f"Duration:     {info['duration']}")
    print(f"Total Words:  {info['total_words']:,}")
    print(f"Total Blocks: {info['total_blocks']}")

    # 3. Search Transcript for Specific Moments
    query = "while loop"
    print(f"\nSearching for '{query}' in tutorial transcript...")
    matches = agent.search_transcript(query, max_results=3)
    for i, match in enumerate(matches, 1):
        print(f"[{i}] At {match['timestamp']} - {match['end_timestamp']}:")
        print(f"    \"{match['text'][:120]}...\"\n")

    # 4. If Groq Key is available, ask questions or generate code
    if groq_api_key:
        print("--- Asking Question to Tutorial Agent ---")
        question = "How does the speaker explain variables and input in Python?"
        print(f"Question: {question}\n")
        
        # Streaming response
        print("Answer (Streaming):")
        for chunk in agent.explain(question, stream=True):
            print(chunk, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    main()
