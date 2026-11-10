# NammaBuildLabs: Telegram flow (no video API needed)

## How it works
1. **Morning (8:00 IST):** the bot sends today's episode: a script, one ready-to-paste Gemini prompt per clip, and the caption.
2. **You (about 5 minutes):** open the Gemini app, Create video, paste each prompt exactly as it is, download the clips, and send them back to the bot (clip 1 first). If you attached a reference photo for her first video, attach the same one.
3. **The bot:** joins the clips, adds the logo, episode tag and captions, and sends a preview with buttons.
4. **You tap a button:**
   - **Post to Instagram and YouTube:** uploads to whichever you have set up.
   - **I will post by hand:** the bot sends the final file and the caption, and you upload them yourself.
   - **Redo the clips** or **Skip today**.

Scripts are written by Gemini when `GEMINI_API_KEY` is set (a free key works for text). If there is no key, or Gemini is overloaded, a plain template script is used so the bot always has something to send. Nothing here needs paid API billing.

## Nammi always looks the same
Every prompt starts with the same fixed description of Nammi, copied word for word from the prompt that made your approved video. It lives in `config.yaml` under `series: host_prompt`. Each prompt is built as: **fixed look** + **what she does** + **what she says** + **fixed ending** (`speech_style` and `prompt_ending`). Only the action and the spoken line change. Do not edit `host_prompt` unless you want to change how she looks.

## One-time setup
1. Copy the files from `content-engine-telegram.zip` over your project folder, then `git add -A`, commit and push.
2. In GitHub **Settings, Secrets and variables, Actions** you already have `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`. Optional: `GEMINI_API_KEY` (free key) for better scripts.
3. Open the bot in Telegram and send `/start` once.
4. In **Actions**, run **Telegram daily script** once with **Run workflow** to test. You should receive the script within a minute.
5. The old AI-video workflows (Draft daily content, Publish approved draft, Test Veo) are now manual-only, so they no longer run or fail by themselves.

## Using it every day
- Clips: send them as **files** if you can (paperclip, File) for the best quality. Bots can read files up to 20 MB, which is plenty for 8 to 10 second clips.
- The poll job checks Telegram every 30 minutes (about 07:30 to 00:30 IST), so after you send the clips, wait up to about 30 minutes for the preview. GitHub schedules can also run a few minutes late.
- For an instant reply, run the bot on your own computer instead: `pip install pillow pyyaml requests google-genai`, install ffmpeg, set `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (and optionally `GEMINI_API_KEY`), then `python run.py tg-loop`. Turn off the **Telegram poll** workflow while you do this, because Telegram allows only one listener at a time.

## Bot commands
`/script` send today's script again, `/new` a different script, `/status`, `/done` join the clips sent so far (for example if you only made one), `/redo` start the clips again, `/skip`, `/help`.

## Instagram
Automatic posting uses the Facebook Login route (Page access token, `IG_ACCESS_TOKEN`, `IG_USER_ID`, and the repository variable `IG_GRAPH_BASE` = `https://graph.facebook.com/v26.0`). Until that works, use the **I will post by hand** button. The bot gives you the final file and the caption.

## YouTube Shorts (optional)
1. Google Cloud Console: create a project, enable **YouTube Data API v3**.
2. **OAuth consent screen:** user type External, add yourself as a test user. Then publish the app ("In production"), otherwise Google expires the refresh token after about 7 days while it is in Testing.
3. **Credentials, Create OAuth client ID, Desktop app.** Copy the client ID and secret.
4. On your computer: `YT_CLIENT_ID=... YT_CLIENT_SECRET=... python run.py yt-auth`. Open the address it prints, allow access, and copy the refresh token it prints.
5. Add GitHub secrets `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, and set `youtube_upload: true` in `config.yaml`.
6. **Important:** YouTube locks videos uploaded through the API to **private** until your Google project passes an API compliance audit (it can take weeks). That is why `youtube_privacy` defaults to "private". Check each upload in YouTube Studio. Some sources say you can switch a locked video to public by hand, others say not until the audit passes, so test with your first upload. Until then, uploading Shorts by hand from the file the bot sends is the reliable way.

## If something goes wrong
| Symptom | Likely cause |
|---|---|
| No message in the morning | The **Telegram daily script** run failed; open it in Actions. Check the two Telegram secrets. |
| Bot ignores my clips | Send `/status`. If it says idle, send `/script` first. |
| "Got clip" but no preview | The poll job has not run yet (up to 30 minutes), or ffmpeg failed; open the run log. |
| "has no sound" error | The clip was made without speech. Regenerate it with the spoken line. |
| Instagram: failed | Token or Facebook route not ready. Use **I will post by hand**. |
