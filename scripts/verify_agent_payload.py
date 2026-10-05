"""Tiny real planner-format check, no company research or credential logging."""
import json
import sys
from pathlib import Path
from orglens.agent import SYSTEM, ProviderError, load_env, post_json, providers_from_env

load_env()
state = {"organisation_number": "123456789", "legal_name": "Synthetic AS",
         "availability": {"official_website": "available"}, "claims": [{"id": "fixture", "field": "legal_name", "value": "Synthetic AS"}],
         "candidates": [], "searches_remaining": 0, "steps_remaining": 1}
if len(sys.argv) > 1:
    row = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()[0])
    state = {"organisation_number": row["organisation_number"], "legal_name": row["legal_identity"]["legal_name"],
             "availability": row["availability"], "claims": [{"id": c["id"], "field": c["field"], "value": c["value"]} for c in row["claims"]][:35],
             "candidates": [], "searches_remaining": 2, "steps_remaining": 6}
for p in providers_from_env(["groq", "cloudflare", "cohere"]):
    body = {"model": p["model"], "messages": [{"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(state, ensure_ascii=False)}], "max_tokens": 384, "temperature": 0}
    if p["name"] == "groq":
        body["reasoning_effort"] = "low"
        body["tool_choice"] = "none"
    body["response_format"] = {"type": "json_object"}
    try:
        result = post_json(p["url"], p["key"], body, 15)
        content = "".join(c.get("text", "") for c in result.get("message", {}).get("content", [])) if p["name"] == "cohere" else result["choices"][0]["message"].get("content", "")
        try:
            action = json.loads(content)
            valid = action.get("action") in {"finish", "search", "inspect"}
        except (ValueError, TypeError, AttributeError):
            valid = False
        print(json.dumps({"provider": p["name"], "status": "success", "valid_planner_json": valid, "usage": result.get("usage", {})}))
    except ProviderError as e:
        print(json.dumps({"provider": p["name"], "http_status": e.status, "hints": e.hints}))
