"""
insight_generation_agent.py

PersonaPulse - Insight Generation Agent
------------------------------------------
Sole job: Read all of the reshaped articles for a persona together, and
write ONE short paragraph summarizing the key trends across that whole
set for the week.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- Gemini 3.1 Flash Lite as the reasoning model (ADK native model support,
  no bridge library needed, since Gemini is Google own model)
- No external tool is needed here. Spotting a trend across several
  articles is a pure language reasoning task, so the LLM does it
  directly from instructions.

Assumes:
- Either GOOGLE_API_KEY is set (for Google AI Studio), OR
  GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION are set along with
  GOOGLE_GENAI_USE_VERTEXAI=TRUE (for Vertex AI on GCP)
- Input is the dict produced by content_reshaping_agent, containing a
  persona name and a list of articles, each already carrying its own
  bullet_points field.
"""

from google.adk.agents import LlmAgent

# ---------------------------------------------------------------------------
# 1. The ADK Agent itself - uses Gemini 3.1 Flash Lite to write one insight
# ---------------------------------------------------------------------------

insight_generation_agent = LlmAgent(
    name="insight_generation_agent",
    model="gemini-3.1-flash-lite",
    description="Reads all reshaped articles for a persona together and writes one short trend paragraph.",
    instruction=(
        "You are the Insight Generation Agent in the PersonaPulse pipeline. "
        "You will receive the output from the Content Reshaping Agent: a "
        "persona name and a list of articles, each already rewritten into "
        "bullet points.\n\n"
        "Your task:\n"
        "1. Read ALL of the articles bullet points together, as one set, "
        "not one at a time.\n"
        "2. Identify the main theme or trend that connects several of "
        "these articles this week, from the point of view of this "
        "persona. Look for a pattern, not just a list of unrelated "
        "facts.\n"
        "3. Write EXACTLY ONE short paragraph, 3 to 5 sentences, in "
        "simple plain English, describing that trend.\n"
        "4. Do not repeat the bullet points. Do not list the articles "
        "one by one. Write a genuine summary of the pattern across the "
        "whole set, as if briefing a busy reader in a few seconds.\n"
        "5. Do not invent facts that are not supported by the articles "
        "provided.\n\n"
        "Do not rewrite or reorder the individual articles, that has "
        "already been done by earlier agents. Return the persona name "
        "and this new insight paragraph, plus the original unchanged "
        "list of articles, so the next agent still has everything it "
        "needs to build the final digest.\n\n"
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

    # In the real pipeline, this input comes from the Content Reshaping
    # Agent output. For a standalone test, paste a sample output here.
    sample_input = {
        "persona": "Tech Professional",
        "articles": [
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
            {
                "title": "Cloud provider cuts AI compute prices",
                "url": "https://example.com/cloud-prices",
                "source": "Example News",
                "published_at": "2026-09-23T09:00:00Z",
                "bullet_points": [
                    "A major cloud provider lowered prices for AI compute.",
                    "This makes it cheaper for companies to train models.",
                    "Analysts say this could speed up AI adoption.",
                ],
            },
        ],
    }

    async def main():
        runner = InMemoryRunner(agent=insight_generation_agent, app_name=APP_NAME)

        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate the weekly insight for this persona: {sample_input}")],
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
