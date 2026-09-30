"""
ranking_and_filtering_agent.py

PersonaPulse - Filtering & Ranking Agent
------------------------------------------
Sole job: Take the raw articles returned by the News Fetch Agent and:
  1. Remove duplicate articles.
  2. Rank the remaining articles by relevance to the persona.
  3. Select and return only the top 10.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- Gemini 3.1 Flash Lite as the reasoning model
- Deduplication tool for exact title/URL matches
- Input loaded from data/news_fetch_agent_output.json
- Output saved to data/ranking_and_filtering_agent_output.json
"""

import json
import os
import re
from dotenv import load_dotenv
from google.adk.agents import LlmAgent

# Load environment variables from .env file
load_dotenv()


# ---------------------------------------------------------------------------
# 1. Data I/O Helpers
# ---------------------------------------------------------------------------

def load_news_fetch_output(filename: str = "news_fetch_agent_output.json") -> dict:
    """
    Loads raw news fetch agent output from the data folder.
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
        "Please run 'python agents/news_fetch_agent.py' first to generate it."
    )


def save_ranking_output(data_dict: dict, filename: str = "ranking_and_filtering_agent_output.json") -> str:
    """
    Saves the ranking and filtering agent output into the data folder in strict JSON format.
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


def extract_json(text: str) -> dict:
    """
    Safely extracts and parses a JSON object from text returned by the model.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in output text: {text[:200]}")

    json_str = match.group(0).replace("\\'", "'")
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# 2. Deterministic helper tool - deduplication
# ---------------------------------------------------------------------------

def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    ADK Tool: Removes duplicate articles from a list based on title or URL.
    """
    seen_titles = set()
    seen_urls = set()
    unique_articles = []

    for article in articles:
        title_key = (article.get("title") or "").strip().lower()
        url_key = (article.get("url") or "").strip().lower()

        if title_key in seen_titles or url_key in seen_urls:
            continue

        seen_titles.add(title_key)
        seen_urls.add(url_key)
        unique_articles.append(article)

    return unique_articles


# ---------------------------------------------------------------------------
# 3. The ADK Agent itself
# ---------------------------------------------------------------------------

ranking_and_filtering_agent = LlmAgent(
    name="ranking_and_filtering_agent",
    model="gemini-3.1-flash-lite",
    description="Removes duplicate articles and ranks the rest by relevance, keeping only the top 10 for the persona.",
    instruction=(
        "You are the Filtering and Ranking Agent in the PersonaPulse pipeline. "
        "You will receive the output from the News Fetch Agent: a persona "
        "name, its topics, and a list of raw articles. Follow these steps "
        "in order:\n\n"
        "1. Call the deduplicate_articles tool on the incoming articles "
        "list to remove exact duplicate titles and URLs.\n"
        "2. From the de-duplicated list, judge how relevant each article "
        "is to the persona's stated topics and interests.\n"
        "3. Rank the articles from most to least relevant.\n"
        "4. Select ONLY the top 10 most relevant articles. If fewer than "
        "10 remain after deduplication, return all of them - do not "
        "invent extra articles.\n\n"
        "Do not rewrite, summarize, or shorten the articles - that is the "
        "job of the next agent in the pipeline. Return the persona name "
        "and the final list of up to 10 articles, in ranked order, "
        "unchanged apart from the ranking/filtering itself.\n\n"
        "IMPORTANT: Reply with ONLY a valid JSON object. Do not include "
        "any explanation, headings, or extra words before or after the "
        "JSON. Do not wrap it in code fences. Your entire reply must be "
        "parseable as JSON on its own."
    ),
    tools=[deduplicate_articles],
)


# ---------------------------------------------------------------------------
# 4. Terminal Execution Test Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    APP_NAME = "persona_pulse"
    USER_ID = "test_user"
    SESSION_ID = "test_session"

    print("=" * 60)
    print(" PersonaPulse - Ranking & Filtering Agent Execution Test ")
    print("=" * 60)

    try:
        print("\n[Step 1] Loading input from data/news_fetch_agent_output.json...")
        input_data = load_news_fetch_output()
        print(f"  - Persona: {input_data.get('persona')}")
        print(f"  - Raw Article Count: {input_data.get('article_count', len(input_data.get('articles', [])))}")
    except Exception as e:
        print(f"[ERROR] {e}")
        exit(1)

    async def main():
        print("\n[Step 2] Running Ranking and Filtering Agent...")
        runner = InMemoryRunner(agent=ranking_and_filtering_agent, app_name=APP_NAME)

        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Rank and filter these articles for the persona: {json.dumps(input_data)}")],
        )

        final_text = ""
        last_tool_output = None
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "function_response", None):
                        last_tool_output = part.function_response.response
                    if part.text:
                        final_text += part.text

        if not final_text.strip() and last_tool_output:
            final_text = json.dumps(last_tool_output)

        output_json = extract_json(final_text)

        print("\n[Step 3] Saving output to data/ranking_and_filtering_agent_output.json...")
        save_ranking_output(output_json)

        print("\nRanked Output Summary:")
        print(f"  - Persona: {output_json.get('persona')}")
        articles = output_json.get("articles", [])
        print(f"  - Top Ranked Articles Count: {len(articles)}")

        print("\nTop Ranked Articles Preview:")
        for idx, art in enumerate(articles[:10], 1):
            print(f"  {idx}. {art.get('title')} ({art.get('source')})")

        print("\n[COMPLETE] Ranking and Filtering Agent executed cleanly!")

    asyncio.run(main())
    print("=" * 60)
