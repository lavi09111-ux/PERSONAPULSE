"""
presentation_agent.py

PersonaPulse - Presentation Agent
------------------------------------------
Sole job: Package the insight paragraph and the bullet-pointed articles
into one final, clean, structured digest, ready to be shown to the user
through the web interface.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- No LLM is used here. Packaging already-finished data into a fixed
  shape is a pure formatting task, not a reasoning task, so this agent
  is plain deterministic Python wrapped as an ADK tool/agent. This keeps
  the pipeline honest: only agents that genuinely need to reason use an
  LLM.

Assumes:
- Input is the dict produced by insight_generation_agent, containing a
  persona name, an insight paragraph, and a list of bullet-pointed
  articles.
"""

from datetime import datetime, timezone


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
# Quick manual test (run this file directly to sanity-check the function)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    sample_persona = "Tech Professional"
    sample_insight = (
        "This week AI is becoming cheaper and more accessible. A major "
        "lab released a stronger, lower cost model, a developer tools "
        "startup raised new funding to grow its team, and a cloud "
        "provider cut prices for AI compute. Together these signal "
        "that building with AI is getting easier and less expensive "
        "for companies of all sizes."
    )
    sample_articles = [
        {
            "title": "New AI model released by major lab",
            "url": "https://example.com/ai-model",
            "source": "Example News",
            "published_at": "2026-09-25T10:00:00Z",
            "bullet_points": [
                "A research lab released a new AI model.",
                "It is better at reasoning and coding tasks.",
                "The model is cheaper to use than the older version.",
            ],
        },
        {
            "title": "Startup raises funding round",
            "url": "https://example.com/startup-funding",
            "source": "Example News",
            "published_at": "2026-09-24T09:00:00Z",
            "bullet_points": [
                "A developer tools startup received new funding.",
                "A well-known firm led the investment.",
                "The company plans to hire more engineers.",
                "The startup will use the money to grow globally.",
            ],
        },
    ]

    final_digest = build_final_digest(sample_persona, sample_insight, sample_articles)
    print(json.dumps(final_digest, indent=2))
