# Регенерирует подписанный snapshot.json и пушит в GitHub.
# Запускается Windows Task Scheduler каждую минуту.
#
# Логи в logs/update_and_push.log (последние ~1000 строк).

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"

$ROOT = "C:\Users\icap\OneDrive\Рабочий стол\polymarket_monetization"
$ORACLE = "$ROOT\oracle"
$LOG_DIR = "$ORACLE\logs"
$LOG = "$LOG_DIR\update_and_push.log"

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

function Log($msg) {
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $LOG -Value "[$ts] $msg" -Encoding UTF8
}

# Ротация лога если >500 KB
if ((Test-Path $LOG) -and (Get-Item $LOG).Length -gt 500KB) {
  Get-Content $LOG -Tail 500 | Set-Content "$LOG.tmp" -Encoding UTF8
  Move-Item "$LOG.tmp" $LOG -Force
}

Log "=== update start ==="
Set-Location $ROOT

# 1. Пересобрать snapshot
$build = python -m oracle.build_snapshot 2>&1 | Out-String
Log "build: $($build.Trim())"
if ($LASTEXITCODE -ne 0) {
  Log "FAIL: build_snapshot exit=$LASTEXITCODE — пропускаю push"
  exit 1
}

# 2. Git add / commit / push (если есть изменения)
Set-Location $ORACLE
$status = git status --porcelain public/snapshot.json 2>&1 | Out-String
if (-not $status.Trim()) {
  Log "no changes — skip commit"
  exit 0
}

git add public/snapshot.json 2>&1 | Out-Null
$ts_iso = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$commit = git commit -m "auto: snapshot $ts_iso" 2>&1 | Out-String
Log "commit: $($commit.Trim().Substring(0, [Math]::Min(200, $commit.Trim().Length)))"

$push = git push 2>&1 | Out-String
if ($LASTEXITCODE -eq 0) {
  Log "push OK"
} else {
  Log "PUSH FAIL: $($push.Trim().Substring(0, [Math]::Min(300, $push.Trim().Length)))"
  exit 1
}
Log "=== update done ==="
