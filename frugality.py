#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

HOME = str(Path.home())
FCM_CONFIG_PATH = os.path.join(HOME, ".free-coding-models.json")
CCR_CONFIG_PATH = os.path.join(HOME, ".claude-code-router", "config.json")
OPENCODE_CONFIG_PATH = "opencode.json"


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, shell=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return None


def atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)


def get_fcm_data():
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "frugality_models.json")

        subprocess.run(
            ["stdbuf", "-o0", "free-coding-models", "--json", "--hide-unconfigured"],
            stdout=open(temp_path, "w"),
            stderr=subprocess.PIPE,
            timeout=120,
        )

        with open(temp_path, "r") as f:
            content = f.read()

        os.unlink(temp_path)

        lines = content.split("\n")
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith("["):
                in_json = True
            if in_json:
                json_lines.append(line)
                if line.strip() == "]":
                    break

        return json.loads("\n".join(json_lines))
    except subprocess.TimeoutExpired:
        print("Error: free-coding-models timed out")
        return []
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []
    try:
        start_idx = output.find("[")
        if start_idx == -1:
            return []
        json_str = output[start_idx:]
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []
    try:
        start_idx = output.find("[")
        if start_idx == -1:
            return []
        json_str = output[start_idx:]
        last_bracket = json_str.rfind("]")
        if last_bracket != -1:
            json_str = json_str[: last_bracket + 1]
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []
    try:
        lines = output.strip().split("\n")
        json_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("["):
                json_start = i
                break
        json_output = "\n".join(lines[json_start:])
        return json.loads(json_output)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Could not parse free-coding-models output: {e}")
        return []


def get_fcm_credentials():
    if not os.path.exists(FCM_CONFIG_PATH):
        print(f"Warning: {FCM_CONFIG_PATH} not found")
        return {}
    with open(FCM_CONFIG_PATH, "r") as f:
        return json.load(f)


def map_tiers(models):
    routes = {"default": None, "background": None, "think": None, "longContext": None}

    tier_order = ["S+", "S", "A+", "A", "A-", "B+", "B", "C"]

    for m in models:
        model_id = m.get("modelId", "")

        if not routes["think"] and (
            "r1" in model_id.lower()
            or "v3" in model_id.lower()
            or "reasoning" in model_id.lower()
        ):
            routes["think"] = m
        if not routes["longContext"] and m.get("context_window", 0) >= 32000:
            routes["longContext"] = m
        if not routes["default"] and m.get("tier") in ["S+", "S"]:
            routes["default"] = m
        if not routes["background"] and m.get("tier") in ["A+", "A"]:
            routes["background"] = m

    for role in routes:
        if not routes[role] and routes["default"]:
            routes[role] = routes["default"]

    return routes


def update_configs():
    print("--- Frugality: Discovering Best Free Models ---")

    credentials = get_fcm_credentials()
    if credentials:
        print(f"✓ Found credentials for: {', '.join(credentials.keys())}")
    else:
        print("⚠ No credentials found in ~/.free-coding-models.json")

    models = get_fcm_data()
    if not models:
        print("No models found. Check your Internet/API keys.")
        return

    print(f"✓ Discovered {len(models)} models")

    selected = map_tiers(models)

    if not selected["default"]:
        print("Error: No suitable models found for default role")
        return

    ccr_config = {
        "router": {
            "default": selected["default"]["modelId"],
            "background": selected["background"]["modelId"]
            if selected["background"]
            else selected["default"]["modelId"],
            "think": selected["think"]["modelId"]
            if selected["think"]
            else selected["default"]["modelId"],
            "longContext": selected["longContext"]["modelId"]
            if selected["longContext"]
            else selected["default"]["modelId"],
        }
    }

    os.makedirs(os.path.dirname(CCR_CONFIG_PATH), exist_ok=True)
    atomic_write_json(CCR_CONFIG_PATH, ccr_config)
    print(f"✓ Updated CCR config at {CCR_CONFIG_PATH}")

    opencode_config = {
        "models": [
            {"id": m["modelId"], "tags": [m.get("tier", "unknown")]}
            for m in selected.values()
            if m
        ]
    }
    atomic_write_json(OPENCODE_CONFIG_PATH, opencode_config)
    print(f"✓ Updated {OPENCODE_CONFIG_PATH}")
    print("--- Configuration Complete ---")


if __name__ == "__main__":
    update_configs()
