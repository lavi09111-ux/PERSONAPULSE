"""
insight_generation_agent.py

PersonaPulse - Insight Generation Agent
------------------------------------------
Sole job: Read all of the reshaped articles for a persona together, and
write ONE short paragraph summarizing the key trends across that whole
set for the week.

Stack:
- Google ADK (Agent Development Kit) for the agent wrapper
- Gemini 3.1 Flash Lite as the reasoning model
- Input loaded from data/content_reshaping_agent_output.json
- Output saved to data/insight_generation_agent_output.json
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

def load_reshaping_output(filename: str = "content_reshaping_agent_output.json") -> dict:
    """
    Loads output from the content reshaping agent from the data folder.
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
        "Please run 'python agents/content_reshaping_agent.py' first to generate it."
    )


def save_insight_output(data_dict: dict, filename: str = "insight_generation_agent_output.json") -> str:
    """
    Saves the insight generation agent output into the data folder in strict JSON format.
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
    print(" PersonaPulse - Insight Generation Agent Execution Test ")
    print("=" * 60)

    try:
        print("\n[Step 1] Loading input from data/content_reshaping_agent_output.json...")
        input_data = load_reshaping_output()
        print(f"  - Persona: {input_data.get('persona')}")
        print(f"  - Reshaped Articles Count: {len(input_data.get('articles', []))}")
    except Exception as e:
        print(f"[ERROR] {e}")
        exit(1)

    async def main():
        print("\n[Step 2] Running Insight Generation Agent...")
        runner = InMemoryRunner(agent=insight_generation_agent, app_name=APP_NAME)

        await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate the weekly insight for this persona: {json.dumps(input_data)}")],
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

        print("\n[Step 3] Saving output to data/insight_generation_agent_output.json...")
        save_insight_output(output_json)

        print("\nInsight Generation Output Summary:")
        print(f"  - Persona: {output_json.get('persona')}")
        print(f"  - Article Count Preserved: {len(output_json.get('articles', []))}")
        print("\nGenerated Insight Paragraph:")
        print(f"  \"{output_json.get('insight')}\"")

        print("\n[COMPLETE] Insight Generation Agent executed cleanly!")

    asyncio.run(main())
    print("=" * 60)
