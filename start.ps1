#Requires -Version 5.1
<#
.SYNOPSIS
    SeekTrack Startup Script — starts the attestation agent then Docker services.

.DESCRIPTION
    1. Checks that seektrack_agent.exe is present.
    2. Starts seektrack_agent.exe in the background (if not already running).
       The agent listens on 0.0.0.0:7890 and responds to challenge-response
       requests from the Django backend running inside Docker.
    3. Runs docker-compose up -d.

    How hardware verification works (no fingerprint in any file or env var):
    - Django generates a random nonce and calls http://host.docker.internal:7890/attest
    - The agent computes HMAC-SHA256(key=real_hw_fingerprint, msg=nonce) live
    - Django recomputes the expected HMAC using the fingerprint in license.json
    - If they match → valid; otherwise → blocked
    - Cloning the project to another machine: the agent there computes a different
      fingerprint from that machine's hardware → HMAC mismatch → always blocked.

.NOTES
    Place this file next to docker-compose.yml (project root).
    seektrack_agent.exe must be in the same directory.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -AgentPort 8888 -Detached:$false
#>

param(
    [int]    $AgentPort = 7890,
    [switch] $Detached  = $true
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ─── Paths ────────────────────────────────────────────────────────────────────

$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$AGENT_EXE   = Join-Path $SCRIPT_DIR 'seektrack.exe'
$DOCKER_FILE = Join-Path $SCRIPT_DIR 'docker-compose.yml'

# ─── Preflight Checks ─────────────────────────────────────────────────────────

if (-not (Test-Path $AGENT_EXE)) {
    Write-Error @"
seektrack.exe not found at:
  $AGENT_EXE

Please build it first:
  cd generate_license
  python build_agent.py
"@
    exit 1
}

if (-not (Test-Path $DOCKER_FILE)) {
    Write-Error "docker-compose.yml not found at: $DOCKER_FILE"
    exit 1
}

if (-not (Get-Command 'docker-compose' -ErrorAction SilentlyContinue) -and
    -not (Get-Command 'docker' -ErrorAction SilentlyContinue)) {
    Write-Error 'docker or docker-compose is not available in PATH.'
    exit 1
}

# ─── Step 1: Start attestation agent (if not already running) ─────────────────

Write-Host '[1/2] Checking attestation agent...' -ForegroundColor Cyan

$agentRunning = Get-NetTCPConnection -LocalPort $AgentPort -State Listen -ErrorAction SilentlyContinue
if ($agentRunning) {
    Write-Host "      Agent already listening on port $AgentPort — skipping launch." -ForegroundColor Green
} else {
    Write-Host "      Starting seektrack.exe --agent $AgentPort..." -ForegroundColor Cyan
    Start-Process -FilePath $AGENT_EXE -ArgumentList "--agent", $AgentPort -WindowStyle Hidden
    # Give the agent a moment to bind
    Start-Sleep -Milliseconds 1500
    $agentRunning = Get-NetTCPConnection -LocalPort $AgentPort -State Listen -ErrorAction SilentlyContinue
    if (-not $agentRunning) {
        Write-Error "Agent failed to start on port $AgentPort. Check seektrack.exe manually."
        exit 1
    }
    Write-Host "      Agent started (PID: $((Get-NetTCPConnection -LocalPort $AgentPort -State Listen).OwningProcess))." -ForegroundColor Green
}

# ─── Step 2: Start Docker services ────────────────────────────────────────────

Write-Host '[2/2] Starting Docker services...' -ForegroundColor Cyan

if ($Detached) {
    docker-compose --file $DOCKER_FILE up -d
} else {
    docker-compose --file $DOCKER_FILE up
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "docker-compose exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host 'Services started successfully.' -ForegroundColor Green


.DESCRIPTION
    1. Runs fingerprint_collector.exe --headless to compute a raw hardware fingerprint
       (SHA-256 of MAC + Hostname + BIOS Serial) from the Windows host.

    2. Derives a DAILY ROTATING TOKEN:
         token = HMAC-SHA256(key=raw_fingerprint, msg=UTC_date_YYYYMMDD)
       The token changes every day at midnight UTC.

    3. Sets HOST_FINGERPRINT_TOKEN as a process-scope environment variable only.
       It is NEVER written to disk.

    4. Runs docker-compose up -d.

    5. Clears HOST_FINGERPRINT_TOKEN immediately after docker-compose returns.

    Security model:
    - Even if someone captures HOST_FINGERPRINT_TOKEN via "printenv" or
      "docker inspect", it is only valid for the current UTC day.
    - Copying the token to another machine does NOT help after midnight.
    - On the attacker's machine, start.ps1 will produce a different raw
      fingerprint → different HMAC → does not match license.json → blocked.

.NOTES
    Place this file next to docker-compose.yml (project root).
    fingerprint_collector.exe must be in the same directory.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Detached:$false   # run in foreground (docker-compose up, not up -d)
#>

param(
    [switch] $Detached = $true   # $true = docker-compose up -d (default)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ─── Paths ────────────────────────────────────────────────────────────────────

$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$COLLECTOR   = Join-Path $SCRIPT_DIR 'fingerprint_collector.exe'
$DOCKER_FILE = Join-Path $SCRIPT_DIR 'docker-compose.yml'

# ─── Preflight Checks ─────────────────────────────────────────────────────────

if (-not (Test-Path $COLLECTOR)) {
    Write-Error @"
fingerprint_collector.exe not found at:
  $COLLECTOR

Please make sure it is in the same folder as start.ps1.
"@
    exit 1
}

if (-not (Test-Path $DOCKER_FILE)) {
    Write-Error "docker-compose.yml not found at: $DOCKER_FILE"
    exit 1
}

if (-not (Get-Command 'docker-compose' -ErrorAction SilentlyContinue) -and
    -not (Get-Command 'docker' -ErrorAction SilentlyContinue)) {
    Write-Error 'docker or docker-compose is not available in PATH.'
    exit 1
}

# ─── Step 1: Compute raw hardware fingerprint ─────────────────────────────────

Write-Host '[1/4] Computing hardware fingerprint...' -ForegroundColor Cyan
$rawFingerprint = & $COLLECTOR --headless 2>&1

if ($LASTEXITCODE -ne 0 -or -not $rawFingerprint -or $rawFingerprint.Length -ne 64) {
    Write-Error "fingerprint_collector.exe failed or returned unexpected output: '$rawFingerprint'"
    exit 1
}

Write-Host "      Raw fingerprint: $($rawFingerprint.Substring(0, 16))... (OK)" -ForegroundColor Green

# ─── Step 2: Derive daily rotating HMAC token ─────────────────────────────────

Write-Host '[2/4] Deriving daily HMAC token...' -ForegroundColor Cyan

$utcDate = [System.DateTime]::UtcNow.ToString('yyyyMMdd')   # e.g. "20260421"
$keyBytes = [System.Text.Encoding]::UTF8.GetBytes($rawFingerprint)
$msgBytes = [System.Text.Encoding]::UTF8.GetBytes($utcDate)

$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = $keyBytes
$tokenBytes = $hmac.ComputeHash($msgBytes)
$hmac.Dispose()

$dailyToken = [System.BitConverter]::ToString($tokenBytes).Replace('-', '').ToLower()
# $dailyToken is a 64-char hex string, changes every UTC day

Write-Host "      Token (today $utcDate): $($dailyToken.Substring(0, 16))... (OK)" -ForegroundColor Green

# ─── Step 3: Set token as ephemeral env var ───────────────────────────────────

Write-Host '[3/4] Setting HOST_FINGERPRINT_TOKEN (process scope only — not written to disk)...' -ForegroundColor Cyan

# Process-scope ONLY — never written to Registry, disk, or .env
$env:HOST_FINGERPRINT_TOKEN = $dailyToken

# Immediately overwrite the raw fingerprint variable so it isn't in memory longer than needed
$rawFingerprint = $null
$keyBytes = $null

# ─── Step 4: Start Docker ─────────────────────────────────────────────────────

try {
    Write-Host '[4/4] Starting Docker services...' -ForegroundColor Cyan

    if ($Detached) {
        docker-compose --file $DOCKER_FILE up -d
    } else {
        docker-compose --file $DOCKER_FILE up
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker-compose exited with code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    Write-Host 'Services started successfully.' -ForegroundColor Green
} finally {
    # Remove token from process environment — it now only lives inside the container
    Remove-Item Env:\HOST_FINGERPRINT_TOKEN -ErrorAction SilentlyContinue
    $dailyToken = $null
    Write-Host 'HOST_FINGERPRINT_TOKEN cleared from process environment.' -ForegroundColor DarkGray
}
