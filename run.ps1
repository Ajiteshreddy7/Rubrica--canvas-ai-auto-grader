# Canvas Auto-Grading Daemon - Run Script
# 
# Usage:
#   .\run.ps1           # Run in mock mode (fast, for testing)
#   .\run.ps1 --no-mock # Run in AI mode (real grading with Copilot)
#
# This script automatically configures:
# - Python 3.11.14 from grader conda environment (required for Copilot SDK)
# - GitHub CLI path for repo cloning
# - Copilot CLI path for AI grading

# Set environment variables
$env:COPILOT_CLI_PATH = "C:\Users\ajite\AppData\Roaming\npm\copilot.cmd"
$env:PATH += ";C:\Users\ajite\AppData\Roaming\npm"
$env:PATH += ";C:\Program Files\GitHub CLI"

# Use Python from grader environment (Python 3.11.14 - required for Copilot SDK)
$PYTHON = "C:\Users\ajite\anaconda3\envs\grader\python.exe"

# Verify Python exists
if (-not (Test-Path $PYTHON)) {
    Write-Host "ERROR: Python not found at $PYTHON" -ForegroundColor Red
    Write-Host "Please ensure the 'grader' conda environment is created." -ForegroundColor Yellow
    exit 1
}

# Show header
$MODE = if ($args -contains "--no-mock") { "AI (Copilot Claude Sonnet 4.5)" } else { "Mock (Testing)" }
Write-Host "`n🤖 Canvas Auto-Grading Daemon" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "Mode: $MODE" -ForegroundColor $(if ($args -contains "--no-mock") { "Green" } else { "Yellow" })
Write-Host "Python: 3.11.14 (grader environment)" -ForegroundColor Green
Write-Host "GitHub CLI: $(if (Get-Command gh -ErrorAction SilentlyContinue) { 'Authenticated' } else { 'Not found' })" -ForegroundColor $(if (Get-Command gh -ErrorAction SilentlyContinue) { "Green" } else { "Red" })
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# Run the daemon
& $PYTHON daemon_new.py $args
