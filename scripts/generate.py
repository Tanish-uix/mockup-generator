"""
Mockup generator script.

What it does, step by step:
1. Reads which mockup types you selected (passed in as an env var, comma-separated ids
   matching config/mockup-types.json).
2. Reads your logo (decoded from base64, passed in as an env var).
3. For each selected mockup type:
   a. Reads the prompt template file (prompts/mockup-types/<id>.md)
   b. Sends the PROMPT text to Gemini 2.5 Flash Image ("Nano Banana") to generate a
      background image - this is Google's free-tier image model (500 requests/day free).
   c. Pastes your logo on top of that background at the PLACEMENT coordinates from the template
   d. Saves the final image into outputs/
   If one mockup type fails (e.g. hits a rate limit), it's skipped and the rest continue.
4. GitHub Actions (not this script) then uploads everything in outputs/ to a Release.

Environment variables this script expects (all set by the GitHub Actions workflow):
  GEMINI_API_KEY   - your Gemini API key (stored as a GitHub secret)
  SELECTED_TYPES    - comma-separated mockup ids, e.g. "mug,tshirt"
  LOGO_BASE64        - your logo image encoded as base64 text
"""

import os
import re
import io
import base64
import time
import json
import requests
from PIL import Image

GEMINI_MODEL = "gemini-2.5-flash-image"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
CONFIG_PATH = "config/mockup-types.json"
OUTPUT_DIR = "outputs"


def load_prompt_template(path):
    with open(path, "r") as f:
        content = f.read()

    prompt_match = re.search(r"PROMPT:\s*(.+?)\n\s*PLACEMENT:", content, re.DOTALL)
    if not prompt_match:
        raise ValueError(f"Could not find PROMPT section in {path}")
    prompt = prompt_match.group(1).strip()

    placement = {}
    for key in ["x", "y", "width", "height"]:
        m = re.search(rf"{key}:\s*([\d.]+)", content)
        if m:
            placement[key] = float(m.group(1))
        else:
            raise ValueError(f"Could not find placement value '{key}' in {path}")

    return prompt, placement


def generate_background(prompt, api_key, retries=3):
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    for attempt in range(retries):
        response = requests.post(GEMINI_URL, headers=headers, params=params, json=payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            for part in parts:
                if "inlineData" in part:
                    image_bytes = base64.b64decode(part["inlineData"]["data"])
                    return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            raise RuntimeError(f"Gemini response had no image data: {json.dumps(data)[:500]}")

        # Rate limited or model temporarily overloaded - wait and retry
        if response.status_code in (429, 503):
            wait_time = 20
            print(f"Gemini busy (status {response.status_code}), waiting {wait_time}s before retry ({attempt + 1}/{retries})...")
            time.sleep(wait_time)
            continue

        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:500]}")

    raise RuntimeError("Gemini did not respond successfully in time. Try running the workflow again.")


def composite_logo(background, logo, placement):
    bg_w, bg_h = background.size

    target_w = int(placement["width"] * bg_w)
    target_h = int(placement["height"] * bg_h)
    paste_x = int(placement["x"] * bg_w)
    paste_y = int(placement["y"] * bg_h)

    logo_resized = logo.copy()
    logo_resized.thumbnail((target_w, target_h), Image.LANCZOS)

    result = background.copy()
    # Use the logo's own alpha channel as the paste mask so transparency is respected
    result.paste(logo_resized, (paste_x, paste_y), logo_resized)

    return result.convert("RGB")


def main():
    api_key = os.environ["GEMINI_API_KEY"]
    selected_types = os.environ["SELECTED_TYPES"].split(",")
    logo_base64 = os.environ["LOGO_BASE64"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logo_bytes = base64.b64decode(logo_base64)
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    type_lookup = {t["id"]: t for t in config["mockup_types"]}

    for type_id in selected_types:
        type_id = type_id.strip()
        if type_id not in type_lookup:
            print(f"Skipping unknown mockup type: {type_id}")
            continue

        mockup_info = type_lookup[type_id]
        print(f"Generating: {mockup_info['label']}...")

        try:
            prompt, placement = load_prompt_template(mockup_info["prompt_file"])
            background = generate_background(prompt, api_key)
            final_image = composite_logo(background, logo, placement)

            output_path = os.path.join(OUTPUT_DIR, f"{type_id}.png")
            final_image.save(output_path)
            print(f"Saved: {output_path}")
        except Exception as e:
            # Don't let one failed mockup (e.g. hit a rate limit) take down the
            # whole run - keep whatever succeeded and report what didn't at the end.
            print(f"FAILED to generate {mockup_info['label']}: {e}")
            continue

    print("Done. Finished processing all requested mockup types.")


if __name__ == "__main__":
    main()
