"""
server.py

PersonaPulse - Web API Server & Static Frontend Host
--------------------------------------------------
Serves the Flask web application, REST endpoints for personas, digests,
live agent pipeline runs, and intermediate agent output artifacts.
"""

import asyncio
import json
import os
import sys

# Ensure immediate unbuffered output on Windows stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add agents directory to sys.path so we can import agents easily
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if AGENTS_DIR not in sys.path:
    sys.path.insert(0, AGENTS_DIR)

from news_fetch_agent import load_personas, save_output_to_data_folder
from pipeline import run_pipeline

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_data_file(filename: str):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def save_data_file(filename: str, content: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2)


# ---------------------------------------------------------------------------
# Routes: Static Frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    if os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


# ---------------------------------------------------------------------------
# API Routes: Personas & Digests
# ---------------------------------------------------------------------------

@app.route("/api/personas", methods=["GET"])
def api_get_personas():
    try:
        personas = load_personas()
        return jsonify({"success": True, "personas": personas})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/personas", methods=["POST"])
def api_create_persona():
    try:
        data = request.json or {}
        persona_id = data.get("id", "").strip().lower().replace(" ", "_")
        display_name = data.get("display_name", "").strip()
        topics = data.get("topics", [])
        exclude_keywords = data.get("exclude_keywords", [])

        if not persona_id or not display_name or not topics:
            return jsonify({"success": False, "error": "Missing required fields: id, display_name, topics"}), 400

        personas = load_personas()
        personas[persona_id] = {
            "display_name": display_name,
            "topics": topics if isinstance(topics, list) else [t.strip() for t in str(topics).split(",") if t.strip()],
            "exclude_keywords": exclude_keywords if isinstance(exclude_keywords, list) else [k.strip() for k in str(exclude_keywords).split(",") if k.strip()]
        }

        save_data_file("personas.json", personas)
        return jsonify({"success": True, "persona_id": persona_id, "personas": personas})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/digests", methods=["GET"])
def api_get_all_digests():
    all_digests = get_data_file("all_personas_digests.json")
    if not all_digests:
        all_digests = {}
    return jsonify({"success": True, "digests": all_digests})


@app.route("/api/digests/<persona_id>", methods=["GET"])
def api_get_persona_digest(persona_id):
    personas = load_personas()
    persona_info = personas.get(persona_id)
    if not persona_info:
        return jsonify({"success": False, "error": f"Persona '{persona_id}' not found"}), 404

    display_name = persona_info.get("display_name", persona_id)

    all_digests = get_data_file("all_personas_digests.json")
    if all_digests and persona_id in all_digests:
        return jsonify({"success": True, "digest": all_digests[persona_id], "source": "all_personas_digests"})

    # Check presentation output fallback
    presentation_out = get_data_file("presentation_agent_output.json")
    if presentation_out and presentation_out.get("persona") == display_name:
        return jsonify({"success": True, "digest": presentation_out, "source": "presentation_agent_output"})

    return jsonify({"success": False, "error": f"No digest available for persona '{persona_id}'. Please run the pipeline."}), 444


# ---------------------------------------------------------------------------
# API Routes: Live Pipeline Execution
# ---------------------------------------------------------------------------

@app.route("/api/pipeline/run", methods=["POST"])
def api_run_pipeline():
    try:
        data = request.json or {}
        persona_id = data.get("persona_id")
        personas = load_personas()

        if not persona_id or persona_id not in personas:
            return jsonify({"success": False, "error": f"Invalid persona_id: '{persona_id}'"}), 400

        # Run pipeline in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            digest = loop.run_until_complete(run_pipeline(persona_id))
        finally:
            loop.close()

        # Also update all_personas_digests.json
        all_digests = get_data_file("all_personas_digests.json") or {}
        all_digests[persona_id] = digest
        save_data_file("all_personas_digests.json", all_digests)

        return jsonify({
            "success": True,
            "persona_id": persona_id,
            "digest": digest
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# API Routes: Multi-Agent Intermediate Artifacts
# ---------------------------------------------------------------------------

@app.route("/api/agent-artifacts", methods=["GET"])
def api_get_artifacts():
    artifacts = {
        "step1_news_fetch": get_data_file("news_fetch_agent_output.json"),
        "step2_ranking": get_data_file("ranking_and_filtering_agent_output.json"),
        "step3_reshaping": get_data_file("content_reshaping_agent_output.json"),
        "step4_insight": get_data_file("insight_generation_agent_output.json"),
        "step5_presentation": get_data_file("presentation_agent_output.json")
    }
    return jsonify({"success": True, "artifacts": artifacts})


# ---------------------------------------------------------------------------
# Main Launcher
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print(" PersonaPulse - Web API Server Running ")
    print(" Listening on http://127.0.0.1:5000 ")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

