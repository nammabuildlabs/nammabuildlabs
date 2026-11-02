# NammaBuildLabs content engine: step-by-step setup

Plan for about 1.5 to 2 hours the first time. Never paste a key or token into a chat; put them only in GitHub Secrets.

## What you need (all have free sign-ups)
| Account | Used for | Cost |
|---|---|---|
| GitHub | runs the engine on a schedule | free for a private repo (check current Actions limits) |
| Google AI Studio (Gemini API) | Gemini writes the scripts and Veo makes the Nammi video, one key for both | text is cheap, video is paid per second and is the main cost |
| A second, public GitHub repo (GitHub Pages) | hosts each finished video at a public link so Instagram can fetch it | free |
| Telegram | sends you the preview | free |
| Meta developer account | permission to post to Instagram | free |
| Instagram professional account | the page itself | free |

---
## Step 1: Put the code on GitHub
1. Unzip `content-engine.zip`. Open the folder `content-engine`.
2. Create a free GitHub account, then **New repository**: name `namma-content-engine`, set it to **Private**, do not add a README.
3. Install Git (git-scm.com). In a terminal inside the `content-engine` folder run:
```
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/namma-content-engine.git
git push -u origin main
```
4. On GitHub, click **Actions**. You should see: Draft daily content, Publish approved draft, Hold today's post, Test Veo (one clip), Weekly health check. If you don't, the hidden `.github` folder didn't upload. Use the git commands above, not drag and drop.

## Step 2: Set your start date
Open `config.yaml` on GitHub (pencil icon). Change `start_date` to the day your first video should be Day 1, for example tomorrow's date, then commit. Keep `daily_format: "series"`.

## Step 3: Gemini key (writes the script and makes the video) and test it
1. aistudio.google.com, sign in, **Get API key**. Turn on billing for that project, since Veo video is paid.
2. Add secret `GEMINI_API_KEY`. This one key is used for both the scripts and the video.
3. GitHub: **Actions**, **Test Veo (one clip)**, **Run workflow**. Wait a few minutes. It first tests the script writer, then makes one clip.
4. Open the run log and check the script it printed. Then scroll to **Artifacts**, download `veo-test-clip`, and watch it. Nammi should look like the reference and say the test line.
5. If it fails, copy the error text from the run log and bring it to Claude with the file `src/veo.py`.

## Step 4: Free public hosting for the videos (GitHub Pages)
Google keeps a generated video for only about 2 days and it needs your API key to download, so Instagram can't fetch it from there. The engine downloads each video right away and puts a copy on a free public link.
1. On GitHub, create a second repository named `namma-media`. Set it to **Public** and tick **Add a README**.
2. In that repo: **Settings**, **Pages**, under **Build and deployment** choose **Deploy from a branch**, branch `main`, folder `/ (root)`, **Save**. Your site address will be `https://YOUR-USERNAME.github.io/namma-media`.
3. Create an access token: your profile photo, **Settings**, **Developer settings**, **Personal access tokens**, **Fine-grained tokens**, **Generate new token**. Under repository access choose **Only select repositories** and pick `namma-media`. Under permissions set **Contents: Read and write**. Choose an expiry (1 year) and copy the token.
4. In your main repo (`namma-content-engine`) add three secrets: `MEDIA_REPO` = `YOUR-USERNAME/namma-media`, `MEDIA_TOKEN` = the token, `PUBLIC_BASE` = `https://YOUR-USERNAME.github.io/namma-media`.
5. Notes: everything in this repo is public, which is fine because the videos are posted publicly anyway. A new file can take 1 to 2 minutes to appear, so the Telegram preview link may not open immediately. A weekly job deletes videos older than 21 days. The repo's history keeps growing slowly, so if it ever gets near 1 GB, create a fresh `namma-media` repo and update `MEDIA_REPO` and `PUBLIC_BASE`. Set a reminder to renew the token before it expires.
6. Prefer a bucket (Cloudflare R2 or similar)? The code supports it too: skip `MEDIA_REPO` and set `R2_ENDPOINT`, `R2_BUCKET`, `R2_KEY`, `R2_SECRET` and `PUBLIC_BASE` instead.

## Step 5: Telegram preview bot
1. In Telegram, message **@BotFather**, send `/newbot`, follow the prompts, copy the token.
2. Add secret `TELEGRAM_TOKEN`.
3. Send any message to your new bot. Open `https://api.telegram.org/botYOUR_TOKEN/getUpdates` in a browser and find `"chat":{"id":123456789`. That number is your chat id.
4. Add secret `TELEGRAM_CHAT_ID`.

## Step 6: Instagram posting (the longest step)
1. In the Instagram app: **Settings**, **Account type and tools**, **Switch to professional account**, choose Creator or Business.
2. Go to developers.facebook.com, log in, **My Apps**, **Create app**. Choose the use case **Manage messaging and content on Instagram** and app type Business.
3. In the app dashboard open **Instagram**, then **API setup with Instagram login**. This route needs no Facebook Page.
4. Under **Generate access tokens**, click **Add account**, sign in with namma_build_labs, accept any tester invite, and click **Generate**. Copy the token.
5. Make sure the permissions include `instagram_business_basic` and `instagram_business_content_publish`.
6. Get your account id on the same page, or run: `curl "https://graph.instagram.com/v26.0/me?fields=user_id,username&access_token=YOUR_TOKEN"`. The `user_id` is your Instagram user id.
7. Add secrets `IG_ACCESS_TOKEN` and `IG_USER_ID`.
8. Test: **Actions**, **Weekly health check**, **Run workflow**. Telegram should say "connected as @namma_build_labs".
9. The token lasts about 60 days. Set a reminder every 50 days to refresh it: `curl "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=YOUR_TOKEN"`, then update the secret with the new token.
10. For your own account in Development mode, you normally don't need App Review. Meta changes these screens often, so if a step looks different, follow Meta's current guide.

## Step 7: First real run
1. **Actions**, **Draft daily content**, **Run workflow**. It takes roughly 5 to 15 minutes.
2. Telegram sends the preview link and caption. Watch the video and check the "claims to verify" list.
3. Happy? **Actions**, **Publish approved draft**, **Run workflow**. Check Instagram, and switch on the AI label if the app shows one.

## Step 8: Turn on the daily schedule
- 07:00 IST: the video is drafted and sent to Telegram.
- 09:00 IST: it publishes only if you added the variable `AUTO_PUBLISH` = `true`.
- For the first 7 days leave it off and approve each video yourself.
- After that: repo **Settings**, **Secrets and variables**, **Actions**, **Variables** tab, **New repository variable**, `AUTO_PUBLISH` = `true`.
- To stop one day: **Actions**, **Hold today's post**, **Run workflow** before 09:00.

## Step 9: Monthly checklist
1. Refresh the Instagram token (Step 6.9) and update `IG_ACCESS_TOKEN`.
2. Check Google AI Studio billing, and the `MEDIA_TOKEN` expiry date.
3. Watch for model name changes (`text_model` and `veo_model` in `config.yaml`).
4. Review the last month of posts for errors, and delete old media.

## If something fails
| Symptom | Likely cause |
|---|---|
| No workflows listed | `.github` folder didn't upload; push with git |
| Telegram silent | wrong chat id, or you haven't messaged the bot first |
| Veo or script error | model name changed (see `config.yaml`) or billing not on |
| Instagram error about the token | token expired; refresh it |
| Instagram can't fetch media | Pages not enabled, wrong `PUBLIC_BASE`, or the file was uploaded under 2 minutes ago |
| Draft ran but nothing posted | `AUTO_PUBLISH` is off, so run Publish yourself |
