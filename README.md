# Content Engine

Daily Instagram carousel plus a reel every 3rd day, generated with Claude, rendered with Pillow and FFmpeg,
approved by you, then published through the Instagram Graph API.

## How it works
1. `draft.yml` runs daily at 08:00 IST: picks today's topic from `calendar.json`, asks Gemini for caption, slides and (every 3rd day) a reel script, renders JPEG slides, builds the reel, uploads files to public storage and sends you a Telegram message.
2. You review. In GitHub: Actions > **Publish approved draft** > Run workflow. That is your approval.
3. Optional later: set repository variable `AUTO_PUBLISH=true` and the publish job runs by itself at 12:00 IST. Do this only after about 30 days of drafts that needed no edits.

## Setup
1. Put this folder in a **private** GitHub repo (default branch `main`).
2. Edit `config.yaml`: brand name, handle, colours, `start_date`.
3. Instagram: convert the account to a Professional (Business or Creator) account, link it to a Facebook Page, create a Meta developer app with Instagram content publishing, and generate an access token. Long-lived tokens expire, so note the date and refresh before it lapses. If the Page requires Page Publishing Authorization, complete it first.
4. Public storage: create a Cloudflare R2 (or any S3-compatible) bucket with a public URL. Instagram fetches media from a public URL.
5. Telegram: create a bot with @BotFather and note the chat id.
6. Add repository secrets: `MEDIA_REPO`, `MEDIA_TOKEN`, `PUBLIC_BASE`, `IG_USER_ID`, `IG_ACCESS_TOKEN`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
7. Run **Draft daily content** manually once and check the Telegram message.

## Try it locally (no keys needed)
    pip install -r requirements.txt
    python run.py draft --sample --date 2026-11-02     # renders slides to out/

## Known weak spots
- **Voice:** `edge-tts` is free but unofficial, and cloud IPs are sometimes blocked. If TTS fails on GitHub, replace `_tts()` in `src/reel.py` with another provider.
- **Reels look:** v1 is text scenes with voiceover. Add background music (royalty-free only) or screen recordings later.
- **Review claims:** every draft lists `claims_to_verify`. Check them before approving.
- **Rules:** check Instagram's current rules on labelling AI-generated content, and never publish student work without consent.
- **Tokens and quotas:** Meta tokens expire, and API publishing has daily limits.

## Maintenance routine
- **Daily (5-10 min):** read the Telegram draft, check `claims_to_verify`, tap Publish. No message by 09:00 IST means the draft job failed; you also get a failure alert.
- **Weekly (30 min):** open Instagram insights, note which topics did well, edit `calendar.json` topics. The calendar repeats every 30 days, so refresh it monthly. A Monday health check messages you; no message means check Actions.
- **Monthly:** refresh the Instagram token before it expires, check API and model versions (`GRAPH` in `src/instagram.py`, `model` in `config.yaml`), delete old media from storage, check Instagram's current rules.
- **When something breaks:** copy the error from the failed Actions run and ask Claude, with the relevant file attached. Claude has no memory of past chats unless memory is on, so upload the repo zip or paste the file.

## Mascot host
`reel_style: "mascot"` in `config.yaml` makes an illustrated young-woman host narrate every reel. She is drawn in code (`src/mascot.py`), so her face is identical in every video and there is no per-video cost. Her mouth follows the loudness of the narration, she blinks, and the layout stays inside Instagram's reel safe zone. To change her look (hair, glasses, hoodie colour), edit the `sprite()` function. Introduce her as the illustrated host, not as a real mentor.

## Daily AI video series (9:00 IST)
`daily_format: "series"` in `config.yaml` turns the engine into a daily video series hosted by Nammi.
- **Episodes by complexity** (`projects.json`, 96 projects): beginner = 1 episode, intermediate = 2 parts, advanced = 3 parts. Order is set by `series.rotation`. That gives 193 episodes, about 6 months, then it loops.
- **07:00 IST** `draft.yml`: Gemini writes the episode script (2 lines of 8 seconds), Gemini Omni Flash generates 2 talking clips of Nammi from `assets/host_reference.png`, `src/assemble.py` joins them and adds the logo, episode chip and captions inside Instagram's safe zone, files go to storage, and you get a Telegram preview.
- **09:00 IST** `publish.yml`: posts the reel. It runs by itself only if repository variable `AUTO_PUBLISH` is `true`. Otherwise run "Publish approved draft" yourself.
- **Veto:** run "Hold today's post" before 09:00 to stop that day's publish.
- **Secrets to add:** `GEMINI_API_KEY` (Google AI Studio, billing on) plus the ones listed earlier.
- **First run:** run "Test Veo (one clip)" and download the clip artifact before turning on the schedule. The video model (`video_model` in `config.yaml`) and its Interactions API call are in `src/veo.py`. Veo 3.1 Preview was shut down on 2026-10-22, so the engine now uses Gemini Omni Flash.
- **Offline test:** `DRY_SERIES=1 TEST_CLIP=some.mp4 python run.py draft` builds a layout test with no API keys.
- Captions end with "Hosted by Nammi, our AI virtual host." Also switch on Instagram's AI label when posting.


## Video hosting
Default is a free public GitHub repo served by GitHub Pages (`MEDIA_REPO`, `MEDIA_TOKEN`, `PUBLIC_BASE`). Google keeps generated video for only 2 days and requires your API key to download it, so each clip is saved immediately and re-hosted. R2 or any S3 bucket still works if you set the `R2_*` variables instead. See SETUP-GUIDE.md Step 4.

## Direct upload (no public hosting)
`hosting: "direct"` (default) sends each finished video straight to Instagram with Meta's resumable upload, so no R2 bucket or public link is needed. The 07:00 job saves the video as a GitHub Actions artifact (kept 5 days) and sends it to Telegram as a video; the 09:00 job downloads it and uploads it to Instagram. This needs the Facebook Login route (a Facebook Page, a Page access token and the repository variable `IG_GRAPH_BASE=https://graph.facebook.com/v26.0`). Set `hosting: "public"` to host at a public link instead (R2 or GitHub Pages, any Instagram route). Carousel mode always needs public hosting for its images.
