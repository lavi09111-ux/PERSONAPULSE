"""
presentation_agent.py

PersonaPulse - Presentation Agent
------------------------------------------
Sole job: Package the insight paragraph and the bullet-pointed articles
into one final, clean, structured digest, ready to be shown to the user
through the web interface.

Stack:
- No LLM is used here. Packaging already-finished data into a fixed
  shape is a pure formatting task, not a reasoning task, so this agent
  is plain deterministic Python.
- Input loaded from data/insight_generation_agent_output.json
- Output saved to data/presentation_agent_output.json
"""

import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables if needed
load_dotenv()


# ---------------------------------------------------------------------------
# 1. Data I/O Helpers
# ---------------------------------------------------------------------------

def load_insight_output(filename: str = "insight_generation_agent_output.json") -> dict:
    """
    Loads output from the insight generation agent from the data folder.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "data", filename),
        os.path.join(os.path.dirname(base_dir), "data", filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(
        f"Input file '{filename}' not found in data folder. "
        "Please run 'python agents/insight_generation_agent.py' first to generate it."
    )


def save_presentation_output(data_dict: dict, filename: str = "presentation_agent_output.json") -> str:
    """
    Saves the presentation agent output into the data folder in strict JSON format.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_paths = [
        os.path.join(base_dir, "data", filename),
        os.path.join(os.path.dirname(base_dir), "data", filename),
    ]

    for path in target_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2)

    return target_paths[0]


# ---------------------------------------------------------------------------
# 2. Main Digest Packaging Function
# ---------------------------------------------------------------------------

def build_final_digest(persona: str, insight: str, articles: list[dict]) -> dict:
    """
    Packages the final weekly digest for one persona.

    Args:
        persona: Display name of the persona, e.g. "Tech Professional".
        insight: The one-paragraph trend summary from the Insight
                 Generation Agent.
        articles: List of article dicts, each already carrying a
                  bullet_points field from the Content Reshaping Agent.

    Returns:
        A single dict shaped for the frontend: persona name, generated
        date, the insight paragraph, and a clean list of articles with
        only the fields the frontend actually needs to display
        (title, url, source, published_at, bullet_points), plus an
        empty feedback field per article ready for like/skip input.
    """
    clean_articles = []

    for article in articles:
        clean_articles.append(
            {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "published_at": article.get("published_at", ""),
                "bullet_points": article.get("bullet_points", []),
                "feedback": None,  # will be set to "like" or "skip" by the user later
            }
        )

    return {
        "persona": persona,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "insight": insight,
        "article_count": len(clean_articles),
        "articles": clean_articles,
    }


# ---------------------------------------------------------------------------
# 3. Terminal Execution Test Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print(" PersonaPulse - Presentation Agent Execution Test ")
    print("=" * 60)

    try:
        print("\n[Step 1] Loading input from data/insight_generation_agent_output.json...")
        input_data = load_insight_output()
        print(f"  - Persona: {input_data.get('persona')}")
        print(f"  - Articles Count: {len(input_data.get('articles', []))}")
    except Exception as e:
        print(f"[ERROR] {e}")
        exit(1)

    print("\n[Step 2] Packaging final digest with Presentation Agent...")
    final_digest = build_final_digest(
        persona=input_data.get("persona", ""),
        insight=input_data.get("insight", ""),
        articles=input_data.get("articles", []),
    )

    print("\n[Step 3] Saving final digest to data/presentation_agent_output.json...")
    saved_path = save_presentation_output(final_digest)

    print("\nPresentation Digest Summary:")
    print(f"  - Persona: {final_digest.get('persona')}")
    print(f"  - Generated At: {final_digest.get('generated_at')}")
    print(f"  - Article Count: {final_digest.get('article_count')}")
    print("\nWeekly Insight:")
    print(f"  \"{final_digest.get('insight')}\"")

    print("\nFirst Article in Final Digest:")
    if final_digest.get("articles"):
        art = final_digest["articles"][0]
        print(f"  - Title: {art.get('title')}")
        print(f"  - Source: {art.get('source')}")
        print(f"  - URL: {art.get('url')}")
        print(f"  - Feedback Field Ready: {art.get('feedback')}")

    print("\n[COMPLETE] Presentation Agent executed cleanly!")
    print("=" * 60)
