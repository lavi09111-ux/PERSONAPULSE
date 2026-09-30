"""
content_reshaping_agent.py

PersonaPulse - Content Reshaping Agent
------------------------------------------
Sole job: Take the ranked/filtered top-10 articles from the Ranking and
Filtering Agent and rewrite each one as short, simple English bullet
points, so a reader can scan the whole digest quickly.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- Gemini 3.1 Flash Lite as the reasoning model (ADK native model support,
  no bridge library needed, since Gemini is Google own model)
- No external tool is needed here. Rewriting text into bullet points is
  a pure language task, so the LLM does it directly from instructions.

Assumes:
- Either GOOGLE_API_KEY is set (for Google AI Studio), OR
  GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION are set along with
  GOOGLE_GENAI_USE_VERTEXAI=TRUE (for Vertex AI on GCP)
- Input is the dict produced by ranking_and_filtering_agent, containing
  a persona name and a list of up to 10 ranked articles.
"""

from google.adk.agents import LlmAgent

# ---------------------------------------------------------------------------
# 1. The ADK Agent itself - uses Gemini 3.1 Flash Lite to reshape articles
# ---------------------------------------------------------------------------

content_reshaping_agent = LlmAgent(
    name="content_reshaping_agent",
    model="gemini-3.1-flash-lite",
    description="Rewrites each ranked article into short, simple English bullet points.",
    instruction=(
        "You are the Content Reshaping Agent in the PersonaPulse pipeline. "
        "You will receive the output from the Ranking and Filtering Agent: "
        "a persona name and a list of up to 10 ranked articles, each with "
        "a title, description, url, source, and published_at.\n\n"
        "For EACH article in the list, do the following:\n"
        "1. Read the title and description.\n"
        "2. Rewrite the key point of that article as 3 to 5 short bullet "
        "points, in simple, plain English that a beginner could follow.\n"
        "3. Keep each bullet point to one short sentence. Do not add "
        "opinions, jokes, or extra commentary that was not in the "
        "original article.\n"
        "4. Keep the original title, url, source, and published_at "
        "unchanged, alongside the new bullet points.\n\n"
        "Do not merge articles together, and do not drop any article "
        "from the list. Do not summarize the whole set into one "
        "paragraph here, that is the job of the next agent. Return the "
        "persona name and the full list of articles, each now carrying "
        "a new bullet_points field in addition to its original fields.\n\n"
"IMPORTANT: Reply with ONLY a valid JSON object. Do not include "
"any explanation, headings, or extra words before or after the "
"JSON. Do not wrap it in code fences. Your entire reply must be "
"parseable as JSON on its own."
    ),
)


# ---------------------------------------------------------------------------
# 2. Quick manual test (run this file directly to sanity-check the agent)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from google.adk.runners import InMemoryRunner
    from google.genai import types

    APP_NAME = "persona_pulse"
    USER_ID = "test_user"
    SESSION_ID = "test_session"

    # In the real pipeline, this input comes from the Ranking and
    # Filtering Agent output. For a standalone test, paste a sample
    # output here.
    sample_input = {
        "persona": "Tech Professional",
        "topics": ["technology", "software", "AI", "startups"],
        "articles": [
            {
                "title": "New AI model released by major lab",
                "description": (
                    "A major AI research lab has released a new large "
                    "language model that improves on reasoning tasks "
                    "and coding benchmarks, while lowering the cost per "
                    "request compared to its previous model."
                ),
                "url": "https://example.com/ai-model",
                "source": "Example News",
                "published_at": "2026-09-25T10:00:00Z",
            },
            {
                "title": "Startup raises funding round",
                "description": (
                    "A fast-growing startup building developer tools has "
                    "raised a new funding round led by a well-known "
                    "venture capital firm, to expand its engineering "
                    "team and grow internationally."
                ),
                "url": "https://example.com/startup-funding",
                "source": "Example News",
                "published_at": "2026-09-24T09:00:00Z",
            },
        ],
    }

    async def main():
        runner = InMemoryRunner(agent=content_reshaping_agent, app_name=APP_NAME)

        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Reshape these ranked articles for the persona: {sample_input}")],
        )

        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)

    asyncio.run(main())
