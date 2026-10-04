"""
news_fetch_agent.py

PersonaPulse - News Fetch Agent & MCP Server
--------------------------------------------
Sole job: Given a persona (interests, topics, exclusions), fetch the last 7
days of news articles relevant to that persona using NewsAPI.

Capabilities:
- Google ADK (Agent Development Kit) LlmAgent wrapper
- Model Context Protocol (MCP) Server exposing tools, resources, and prompts
- NewsAPI integration as an external data source
- Output automatically saved to data/news_fetch_agent_output.json
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from mcp.server import MCPServer

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# MCP Server Initialization
# ---------------------------------------------------------------------------
news_mcp_server = MCPServer(name="PersonaPulse-NewsFetch-Server")


# ---------------------------------------------------------------------------
# 1. API Key Check Helper
# ---------------------------------------------------------------------------

def check_news_api_key() -> bool:
    """
    Checks if the NEWSAPI_KEY environment variable is set and valid by making a test request.
    Prints status directly to terminal.
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        print("[ERROR] NEWSAPI_KEY environment variable is missing.")
        return False

    url = "https://newsapi.org/v2/top-headlines"
    try:
        response = requests.get(url, params={"country": "us", "pageSize": 1, "apiKey": api_key}, timeout=10)
        if response.status_code == 200:
            print("[SUCCESS] NewsAPI key is valid and working properly.")
            return True
        else:
            data = response.json()
            print(f"[ERROR] NewsAPI key test failed ({response.status_code}): {data.get('message', response.text)}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to connect to NewsAPI: {e}")
        return False


# ---------------------------------------------------------------------------
# 2. Persona loading from strict JSON file in data folder
# ---------------------------------------------------------------------------

def load_personas() -> dict:
    """
    Loads personas directly from the strict JSON file in the data folder.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "data", "personas.json"),
        os.path.join(os.path.dirname(base_dir), "data", "personas.json"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(f"Personas JSON file not found in paths: {possible_paths}")


# ---------------------------------------------------------------------------
# 3. Output saving helper
# ---------------------------------------------------------------------------

def save_output_to_data_folder(data_dict: dict, filename: str = "news_fetch_agent_output.json") -> str:
    """
    Saves the fetched news agent output into the data folder in strict JSON format.
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
# 4. MCP Tool: Plain Python function that calls NewsAPI
# ---------------------------------------------------------------------------

@news_mcp_server.tool()
def fetch_news_for_topics(topics: list[str], days: int = 7, page_size: int = 20) -> list[dict]:
    """
    MCP Tool: Calls NewsAPI's /everything endpoint and returns raw articles published
    in the last `days` days that match any of the given topics.
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        raise RuntimeError("NEWSAPI_KEY environment variable is not set.")

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    query = " OR ".join(topics)

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": page_size,
            "apiKey": api_key,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "source": article.get("source", {}).get("name"),
            "published_at": article.get("publishedAt"),
        }
        for article in data.get("articles", [])
    ]


# ---------------------------------------------------------------------------
# 5. MCP Tool & ADK Tool: Fetches persona news and persists output
# ---------------------------------------------------------------------------

@news_mcp_server.tool()
def fetch_persona_news(persona_id: str) -> dict:
    """
    MCP Tool & ADK Tool: Fetches the last 7 days of news for a given persona_id,
    and automatically saves the output in data/news_fetch_agent_output.json.
    """
    personas = load_personas()
    persona = personas.get(persona_id)
    if not persona:
        return {"error": f"Unknown persona_id '{persona_id}'. Valid options: {list(personas.keys())}"}

    articles = fetch_news_for_topics(topics=persona["topics"], days=7)

    # Basic exclusion filter - drop articles matching excluded keywords.
    exclude_words = [w.lower() for w in persona.get("exclude_keywords", [])]
    filtered_articles = [
        a for a in articles
        if not any(word in (a.get("title") or "").lower() for word in exclude_words)
    ]

    output_data = {
        "persona": persona["display_name"],
        "topics": persona["topics"],
        "article_count": len(filtered_articles),
        "articles": filtered_articles,
    }

    # Save output to data folder
    save_output_to_data_folder(output_data)

    return output_data


# ---------------------------------------------------------------------------
# 6. MCP Resources & Prompts
# ---------------------------------------------------------------------------

@news_mcp_server.resource("personas://list")
def get_personas_resource() -> str:
    """
    MCP Resource: Exposes the available persona definitions in JSON format.
    """
    try:
        personas = load_personas()
        return json.dumps(personas, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@news_mcp_server.resource("news://latest")
def get_latest_news_resource() -> str:
    """
    MCP Resource: Exposes the latest fetched news output from data/news_fetch_agent_output.json.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_paths = [
        os.path.join(base_dir, "data", "news_fetch_agent_output.json"),
        os.path.join(os.path.dirname(base_dir), "data", "news_fetch_agent_output.json"),
    ]
    for path in target_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

    return json.dumps({"error": "No news output file found. Run fetch_persona_news first."})


@news_mcp_server.prompt("fetch_news_prompt")
def fetch_news_prompt_template(persona_id: str = "tech_professional") -> str:
    """
    MCP Prompt: Provides a formatted instruction prompt for fetching news for a persona.
    """
    return (
        f"You are responsible for fetching news for the persona '{persona_id}'. "
        f"Call the `fetch_persona_news` tool with persona_id='{persona_id}' "
        f"and return the resulting raw JSON payload."
    )


# ---------------------------------------------------------------------------
# 7. The ADK Agent itself
# ---------------------------------------------------------------------------

news_fetch_agent = LlmAgent(
    name="news_fetch_agent",
    model="gemini-3.1-flash-lite",
    description="Fetches the last 7 days of news articles relevant to a chosen persona via MCP/NewsAPI tool.",
    instruction=(
        "You are the News Fetch Agent in the PersonaPulse pipeline. "
        "Your ONLY job is to call the `fetch_persona_news` tool with the "
        "correct persona_id and return its raw output. "
        "Do not summarize, rank, or rewrite the articles - that is the job "
        "of the next agents in the pipeline. "
        "If the persona_id is invalid, clearly report the error returned "
        "by the tool instead of guessing a persona.\n\n"
        "IMPORTANT: Reply with ONLY a valid JSON object (the tool output "
        "itself). Do not include any explanation, headings, or extra "
        "words before or after the JSON. Do not wrap it in code fences. "
        "Your entire reply must be parseable as JSON on its own."
    ),
    tools=[fetch_persona_news],
)


# ---------------------------------------------------------------------------
# 8. Terminal Execution Test Block / MCP Server CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--mcp" in sys.argv:
        print("Starting News Fetch MCP Server over stdio...", file=sys.stderr)
        news_mcp_server.run()
    else:
        print("=" * 60)
        print(" PersonaPulse - News Fetch Agent & MCP Server Test ")
        print("=" * 60)

        print("\n[Step 1] Verifying NEWSAPI_KEY status...")
        is_valid = check_news_api_key()

        if is_valid:
            print("\n[Step 2] Testing MCP tool 'fetch_persona_news' for persona: 'tech_professional'...")
            result = fetch_persona_news("tech_professional")

            print("\n[Step 3] Output saved successfully to data/news_fetch_agent_output.json")
            print("\nFetched Summary:")
            print(f"  - Persona: {result.get('persona')}")
            print(f"  - Topics: {result.get('topics')}")
            print(f"  - Article Count: {result.get('article_count')}")

            print("\nFirst Article Preview:")
            if result.get("articles"):
                first_art = result["articles"][0]
                print(f"  - Title: {first_art.get('title')}")
                print(f"  - Source: {first_art.get('source')}")
                print(f"  - URL: {first_art.get('url')}")

            print("\n[MCP Test] Testing MCP Resource 'personas://list'...")
            personas_res = get_personas_resource()
            print(f"  - Resource payload length: {len(personas_res)} bytes")

            print("\n[COMPLETE] News Fetch Agent & MCP Server verified cleanly!")
        else:
            print("\n[FAILED] Unable to fetch news because NEWSAPI_KEY is invalid or missing.")
        print("=" * 60)
