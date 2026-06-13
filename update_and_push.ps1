# Regenerate signed snapshot.json and push to GitHub.
# Runs via Windows Task Scheduler every minute.
# Logs to logs/update_and_push.log (last ~500 lines).

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Resolve paths relative to script location (avoids issues with non-ASCII
# chars in absolute path like Cyrillic "Рабочий стол").
# $PSScriptRoot points to oracle/ where this file lives.
$ORACLE = $PSScriptRoot
$ROOT = Split-Path -Parent $ORACLE
$LOG_DIR = Join-Path $ORACLE "logs"
$LOG = Join-Path $LOG_DIR "update_and_push.log"

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

function Log($msg) {
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $LOG -Value "[$ts] $msg" -Encoding UTF8
}

# Rotate log if >500 KB
if ((Test-Path $LOG) -and (Get-Item $LOG).Length -gt 500KB) {
  Get-Content $LOG -Tail 500 | Set-Content "$LOG.tmp" -Encoding UTF8
  Move-Item "$LOG.tmp" $LOG -Force
}

Log "=== update start ==="

# 1. Rebuild snapshot (python -m needs cwd == project root for package resolution)
Set-Location $ROOT
$build = python -m oracle.build_snapshot 2>&1 | Out-String
Log "build: $($build.Trim())"
if ($LASTEXITCODE -ne 0) {
  Log "FAIL: build_snapshot exit=$LASTEXITCODE -- skip push"
  exit 1
}

# 2. Git add / commit / push via `git -C <dir>` (no cwd dependence)
$status = git -C $ORACLE status --porcelain public/snapshot.json 2>&1 | Out-String
if (-not $status.Trim()) {
  Log "no changes -- skip commit"
  exit 0
}

git -C $ORACLE add public/snapshot.json 2>&1 | Out-Null
$ts_iso = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$commit = git -C $ORACLE commit -m "auto: snapshot $ts_iso" 2>&1 | Out-String
$commitMsg = $commit.Trim()
if ($commitMsg.Length -gt 200) { $commitMsg = $commitMsg.Substring(0, 200) }
Log "commit: $commitMsg"

$push = git -C $ORACLE push 2>&1 | Out-String
if ($LASTEXITCODE -eq 0) {
  Log "push OK"
} else {
  $pushMsg = $push.Trim()
  if ($pushMsg.Length -gt 300) { $pushMsg = $pushMsg.Substring(0, 300) }
  Log "PUSH FAIL: $pushMsg"
  exit 1
}
Log "=== update done ==="
