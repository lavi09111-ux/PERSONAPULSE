"""
content_reshaping_agent.py

PersonaPulse - Content Reshaping Agent
------------------------------------------
Sole job: Take the ranked/filtered top-10 articles from the Ranking and
Filtering Agent and rewrite each one as short, simple English bullet
points, so a reader can scan the whole digest quickly.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- Gemini 3.1 Flash Lite as the reasoning model
- Input loaded from data/ranking_and_filtering_agent_output.json
- Output saved to data/content_reshaping_agent_output.json
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

def load_ranking_output(filename: str = "ranking_and_filtering_agent_output.json") -> dict:
    """
    Loads output from the ranking and filtering agent from the data folder.
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
        "Please run 'python agents/ranking_and_filtering_agent.py' first to generate it."
    )


def save_reshaping_output(data_dict: dict, filename: str = "content_reshaping_agent_output.json") -> str:
    """
    Saves the content reshaping agent output into the data folder in strict JSON format.
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
        raise ValueError(f"No JSON object found in model output: {text[:200]}")

    json_str = match.group(0).replace("\\'", "'")
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# 2. The ADK Agent itself
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
# 3. Terminal Execution Test Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    APP_NAME = "persona_pulse"
    USER_ID = "test_user"
    SESSION_ID = "test_session"

    print("=" * 60)
    print(" PersonaPulse - Content Reshaping Agent Execution Test ")
    print("=" * 60)

    try:
        print("\n[Step 1] Loading input from data/ranking_and_filtering_agent_output.json...")
        input_data = load_ranking_output()
        print(f"  - Persona: {input_data.get('persona')}")
        print(f"  - Articles to Reshape Count: {len(input_data.get('articles', []))}")
    except Exception as e:
        print(f"[ERROR] {e}")
        exit(1)

    async def main():
        print("\n[Step 2] Running Content Reshaping Agent...")
        runner = InMemoryRunner(agent=content_reshaping_agent, app_name=APP_NAME)

        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Reshape these ranked articles for the persona: {json.dumps(input_data)}")],
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text

        output_json = extract_json(final_text)

        print("\n[Step 3] Saving output to data/content_reshaping_agent_output.json...")
        save_reshaping_output(output_json)

        print("\nReshaped Output Summary:")
        print(f"  - Persona: {output_json.get('persona')}")
        articles = output_json.get("articles", [])
        print(f"  - Reshaped Articles Count: {len(articles)}")

        print("\nReshaped Articles Preview:")
        for idx, art in enumerate(articles[:3], 1):
            print(f"\n  Article {idx}: {art.get('title')}")
            for bullet in art.get("bullet_points", []):
                print(f"    • {bullet}")

        print("\n[COMPLETE] Content Reshaping Agent executed cleanly!")

    asyncio.run(main())
    print("=" * 60)
