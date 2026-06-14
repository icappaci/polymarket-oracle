# Deployment guide

Internal operational notes for running the Polymarket Oracle endpoint. End users don't need this — they just consume `https://polymarket-oracle.istarley2000.workers.dev/snapshot.json`.

The full stack is free and runs on:
- **GitHub** — stores the signed snapshot JSON (public repo)
- **Cloudflare Workers** — serves the JSON with CORS and a 30-second CDN cache
- **Windows Task Scheduler** — rebuilds the snapshot every minute and pushes to GitHub

Total cost: **$0/month** on free tiers.

---

## Architecture

```
Task Scheduler (every 1 min)
  → update_and_push.ps1
    → python -m oracle.build_snapshot   (reads DuckDB, signs with ECDSA)
    → git commit + push                  (to GitHub)
  → GitHub raw URL updated
  → Cloudflare Worker (cache TTL 30s)
    → client gets fresh JSON
```

End-to-end freshness: **60-90 seconds** (cron interval + GitHub CDN propagation + Cloudflare cache window).

---

## One-time setup

### 1. GitHub repo

Create a **public** repo (private won't work — Cloudflare Worker needs to fetch the raw file without auth). Don't initialize with README/license/gitignore — push the local commits as-is.

```powershell
cd <path-to-oracle-folder>
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

Verify the snapshot is reachable:
```
https://raw.githubusercontent.com/<user>/<repo>/main/public/snapshot.json
```

### 2. Cloudflare Worker

Register for free at https://dash.cloudflare.com/sign-up (email only). Confirm the verification email or `wrangler deploy` will fail with "verify your email address".

Install wrangler if needed:
```powershell
npm install -g wrangler
```

Login and deploy:
```powershell
cd <path-to-oracle-folder>
wrangler login            # opens browser for OAuth
wrangler deploy
```

If this is your first Worker, you'll need to register a `workers.dev` subdomain (one-time, via the Cloudflare dashboard onboarding wizard). After that the deploy completes and you get a URL like `https://polymarket-oracle.<handle>.workers.dev`.

Before deploying, edit `worker.js` and update `SNAPSHOT_URL` to point at your GitHub raw URL from step 1. Commit and push that change so the URL is part of the repo history.

### 3. Cron — Windows Task Scheduler

The `update_and_push.ps1` script does the rebuild + commit + push. Register it as a scheduled task that runs every minute. We launch through a small VBS wrapper (`update_silent.vbs`) because `powershell.exe -WindowStyle Hidden` still flashes a console window for ~50ms on each run — annoying when it happens every minute. The VBS wrapper uses the Win32 hide-on-start flag so the window is never created.

```powershell
$vbsPath = "<absolute-path>\oracle\update_silent.vbs"
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\wscript.exe" `
  -Argument "`"$vbsPath`""

$start = (Get-Date).AddSeconds(60)
$trigger = New-ScheduledTaskTrigger -Once -At $start `
  -RepetitionInterval (New-TimeSpan -Minutes 1)

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName "polymarket-oracle-update" `
  -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
  -Description "Rebuild Polymarket Oracle signed snapshot every minute" -Force
```

No admin rights needed. The task runs under the current user with interactive logon (no password required).

Logs go to `oracle/logs/update_and_push.log` (auto-rotated at 500 KB). Wait two minutes after registering and confirm the log shows `push OK` entries.

### 4. Git credentials

The cron task runs `git push` non-interactively. Make sure Windows Credential Manager has cached your GitHub credentials — easiest way is to do one manual `git push` first; the credential manager will prompt and remember the credentials forever after.

---

## Local development

Run the build pipeline manually to test changes:

```bash
python -m oracle.sign_keys generate    # one-time: create signing keypair (private key stays local)
python -m oracle.build_snapshot         # build + sign snapshot
python -m oracle.verify_snapshot        # verify the signature locally
```

The private key lives in `oracle/keys/signing_key.json`. It's listed in `.gitignore` and **must never be committed**. To audit: `git log --all --full-history -- '*signing_key.json'` should return nothing.

The public address (`signing_pubkey.txt`) is committed — that's the address consumers verify signatures against.

---

## Operations checklist

- [ ] GitHub repo public, push works
- [ ] `raw.githubusercontent.com` URL returns the JSON
- [ ] Cloudflare email verified
- [ ] `wrangler login` succeeded
- [ ] `workers.dev` subdomain registered
- [ ] `worker.js` SNAPSHOT_URL points at your GitHub raw URL
- [ ] `wrangler deploy` returns a `*.workers.dev` URL
- [ ] `GET /snapshot.json` returns JSON in a browser
- [ ] `GET /health` returns `{"status":"ok",...}`
- [ ] Task Scheduler entry exists, runs every minute
- [ ] After 5 minutes: `generated_at_unix` in the response is increasing
- [ ] `oracle/logs/update_and_push.log` shows `push OK` lines

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `git push` keeps asking for password | No credential helper | Run `git config --global credential.helper manager` |
| Worker returns 502 `upstream_unavailable` | SNAPSHOT_URL wrong or repo is private | Open the URL in a browser to check |
| Endpoint returns stale snapshot | Cloudflare 30s cache | Wait, or look at the `x-cache: HIT/MISS` header |
| `wrangler deploy` says "verify your email" | Cloudflare account not verified | Click the verify link in your inbox |
| `wrangler deploy` says "register a subdomain" | First time using Workers | Open the URL the error mentions, complete the wizard, deploy again |
| Task Scheduler shows "Access denied" | Wrong run-as user | Set principal to current Interactive user (see setup above) |
| `wrangler deploy` says "quota exceeded" | 100k/day Workers free limit | Wait, or upgrade to $5/mo paid plan |
