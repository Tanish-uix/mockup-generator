"""
Mockup generator script.

What it does, step by step:
1. Reads which mockup types you selected (passed in as an env var, comma-separated ids
   matching config/mockup-types.json).
2. Reads your logo (decoded from base64, passed in as an env var).
3. For each selected mockup type:
   a. Reads the prompt template file (prompts/mockup-types/<id>.md)
   b. Sends the PROMPT text to Hugging Face's free Inference API to generate a background image
   c. Pastes your logo on top of that background at the PLACEMENT coordinates from the template
   d. Saves the final image into outputs/
4. GitHub Actions (not this script) then uploads everything in outputs/ to a Release.

Environment variables this script expects (all set by the GitHub Actions workflow):
  HF_TOKEN         - your Hugging Face API token (stored as a GitHub secret)
  SELECTED_TYPES    - comma-separated mockup ids, e.g. "mug,tshirt"
  LOGO_BASE64        - your logo image encoded as base64 text
"""

import os
import re
import io
import base64
import time
import requests
from PIL import Image

HF_MODEL_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
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


def generate_background(prompt, hf_token, retries=3):
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": prompt}

    for attempt in range(retries):
        response = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)).convert("RGBA")

        # Model still loading on Hugging Face's side - wait and retry
        if response.status_code == 503:
            wait_time = 20
            print(f"Model loading, waiting {wait_time}s before retry ({attempt + 1}/{retries})...")
            time.sleep(wait_time)
            continue

        raise RuntimeError(f"Hugging Face API error {response.status_code}: {response.text}")

    raise RuntimeError("Model did not become ready in time. Try running the workflow again.")


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
    hf_token = os.environ["HF_TOKEN"]
    selected_types = os.environ["SELECTED_TYPES"].split(",")
    logo_base64 = os.environ["LOGO_BASE64"]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logo_bytes = base64.b64decode(logo_base64)
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

    with open(CONFIG_PATH, "r") as f:
        import json
        config = json.load(f)

    type_lookup = {t["id"]: t for t in config["mockup_types"]}

    for type_id in selected_types:
        type_id = type_id.strip()
        if type_id not in type_lookup:
            print(f"Skipping unknown mockup type: {type_id}")
            continue

        mockup_info = type_lookup[type_id]
        print(f"Generating: {mockup_info['label']}...")

        prompt, placement = load_prompt_template(mockup_info["prompt_file"])
        background = generate_background(prompt, hf_token)
        final_image = composite_logo(background, logo, placement)

        output_path = os.path.join(OUTPUT_DIR, f"{type_id}.png")
        final_image.save(output_path)
        print(f"Saved: {output_path}")

    print("Done. All requested mockups generated.")


if __name__ == "__main__":
    main()
