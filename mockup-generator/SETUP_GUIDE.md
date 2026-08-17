# Mockup Generator — Setup Guide

This gets you from zero to a working internal tool. Follow it in order.

---

## What you're building

- A webpage where you upload a logo, tick which mockups you want, click generate
- That triggers a GitHub Action (a free automated job) that:
  - generates a background scene for each mockup type using a free AI image model
  - pastes your logo onto it
  - uploads the results as a GitHub Release you can download

---

## Step 1 — Create a GitHub account (skip if you have one)

Go to https://github.com and sign up. Free.

---

## Step 2 — Create a Hugging Face account + API token

This is the free AI model that generates the mockup backgrounds.

1. Go to https://huggingface.co and sign up (free)
2. Click your profile picture (top right) → **Settings** → **Access Tokens**
3. Click **New token**, name it anything (e.g. `mockup-tool`), choose **Read** access
4. Copy the token somewhere safe — it looks like `hf_xxxxxxxxxxxx`

You'll use this in Step 5.

---

## Step 3 — Create the GitHub repo

1. Go to https://github.com/new
2. Name it `mockup-generator` (or anything you like)
3. Set it to **Private** (recommended, since this is internal)
4. Click **Create repository**

---

## Step 4 — Upload the project files

You have a folder called `mockup-generator` with everything already built. Upload it:

**Easiest way (no command line needed):**
1. On your new repo's GitHub page, click **uploading an existing file**
2. Drag the entire contents of the `mockup-generator` folder in (keep the folder structure — `.github/workflows/generate.yml` needs to stay in that exact path)
3. Scroll down, click **Commit changes**

**If you're comfortable with terminal instead:**
```bash
cd mockup-generator
git init
git add .
git commit -m "Initial setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mockup-generator.git
git push -u origin main
```

---

## Step 5 — Add your Hugging Face token as a secret

This lets the GitHub Action use your Hugging Face token without it being visible in your code.

1. In your repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `HF_TOKEN`
4. Value: paste the `hf_...` token from Step 2
5. Click **Add secret**

---

## Step 6 — Create a Personal Access Token (PAT) for the frontend

This is different from the Hugging Face token — this one lets your webpage trigger the GitHub Action.

1. Go to https://github.com/settings/tokens?type=beta
2. Click **Generate new token**
3. Name it `mockup-tool-trigger`
4. Set **Expiration** to whatever you're comfortable with (e.g. 90 days — you'll need to regenerate it after)
5. Under **Repository access**, choose **Only select repositories** → pick your `mockup-generator` repo
6. Under **Permissions** → **Repository permissions**, find **Actions** and set it to **Read and write**
7. Click **Generate token**
8. Copy the token (starts with `github_pat_...`) — you won't be able to see it again

---

## Step 7 — Open the frontend page

1. In your repo, open `frontend/index.html` directly in your browser — either:
   - Double-click the file on your computer, or
   - Turn on GitHub Pages: **Settings** → **Pages** → set source to `main` branch, `/frontend` folder (note: your `config/` folder is one level up, so if you use GitHub Pages you may need to also enable Pages from the repo root instead, or just open the file locally — local is simplest for solo internal use)

2. On the page:
   - Paste your **Personal Access Token** (from Step 6)
   - Enter your repo as `yourusername/mockup-generator`
   - Upload your logo (PNG with transparent background works best)
   - Tick the mockup types you want
   - Click **Generate Mockups**

---

## Step 8 — Watch it run

1. Go to your repo → **Actions** tab
2. You'll see a run called "Generate Mockups" — click it to watch progress
3. Takes roughly 30–90 seconds per mockup type (Hugging Face's free tier can be slow, especially the first request if the model needs to "wake up" — the script automatically retries if that happens)

---

## Step 9 — Get your mockups

1. Once the Action finishes, go to your repo's **Releases** tab (right sidebar, or `github.com/yourusername/mockup-generator/releases`)
2. You'll see a new release with a timestamp — download the PNG files from there

---

## Adding more mockup types later

1. Add a new entry in `config/mockup-types.json`
2. Create a matching prompt file in `prompts/mockup-types/your-new-type.md` (copy the format of `mug.md`)
3. Commit and push — no other code changes needed

---

## Known limitations of this v1 (worth knowing upfront)

- **Logo placement is a flat paste**, not perspective-warped onto the product — good enough for flat surfaces (business cards, flat-lay tees, straight-on mugs), less convincing on curved/angled surfaces. If quality on a given mockup type isn't good enough, the fix is usually adjusting the `PLACEMENT` x/y/width/height numbers in that mockup's prompt file, or eventually adding perspective transforms.
- **Hugging Face's free Inference API can be slow or rate-limited** under heavy use — fine for occasional internal use, not for high volume.
- **Quality won't match Nano Banana/Gemini** — this is the trade-off for using fully free, open, self-controlled infrastructure instead of a paid API.

---

## If something breaks

- Check the **Actions** tab → click the failed run → click the failed step to see the error log
- Most common issues: missing `HF_TOKEN` secret, malformed prompt template file, or Hugging Face rate limiting (just wait a few minutes and retry)
