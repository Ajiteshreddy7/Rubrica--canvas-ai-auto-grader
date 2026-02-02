# Installing GitHub Copilot CLI on Windows

## Current Status

✅ **GitHub Copilot SDK** (v0.1.0) - Already installed  
❌ **GitHub Copilot CLI** - Not installed (required for AI grading)  
❌ **Node.js/npm** - Not installed (required for CLI installation)

## Why We Need the CLI

The GitHub Copilot SDK (`github-copilot-sdk` Python package) acts as a **wrapper** around the Copilot CLI binary. The architecture is:

```
Python Code (grader.py)
       ↓
GitHub Copilot SDK (Python package)
       ↓
GitHub Copilot CLI (Node.js binary)
       ↓
GitHub Copilot API (OAuth authenticated)
```

**Without the CLI**, the SDK cannot communicate with GitHub's Copilot API.

## Installation Options for Windows

According to [github/copilot-cli README](https://github.com/github/copilot-cli), there are 3 ways to install on Windows:

### Option 1: WinGet (Recommended - No Admin Required)

```powershell
# Install Windows Package Manager if not already installed
# Then run:
winget install GitHub.Copilot
```

**Status**: WinGet not available on this system

### Option 2: npm (Most Common)

```powershell
# First install Node.js (includes npm)
# Then run:
npm install -g @github/copilot
```

**Status**: Node.js/npm not installed

**To Install Node.js**:
1. **Download Installer** (No Admin Required):
   - Visit: https://nodejs.org/
   - Download the LTS version (v25.5.0 as of Jan 2026)
   - Run installer (choose "Install for me only" if no admin rights)
   - Restart PowerShell after installation

2. **Using Chocolatey** (Requires Admin):
   ```powershell
   # Open PowerShell as Administrator
   choco install nodejs -y
   ```
   **Note**: Attempted this but failed due to permissions

### Option 3: Conda (Alternative - Possible Workaround)

```powershell
# Try installing Node.js via conda-forge
conda activate grader
conda install -c conda-forge nodejs -y
```

## Recommended Next Steps

### Step 1: Install Node.js via Conda (Try First)

```powershell
conda activate grader
conda install -c conda-forge nodejs npm -y
node --version
npm --version
```

If successful, proceed to Step 2.

### Step 2: Install Copilot CLI

```powershell
npm install -g @github/copilot
```

### Step 3: Authenticate

```powershell
# Option A: Interactive login
copilot

# Then in the CLI, type:
/login

# Option B: Personal Access Token
# 1. Visit: https://github.com/settings/personal-access-tokens/new
# 2. Add permission: "Copilot Requests"
# 3. Generate token
# 4. Set environment variable:
$env:GITHUB_TOKEN = "your_token_here"
```

### Step 4: Test AI Grading

```powershell
conda activate grader

# Verify dependencies
python verify_deps.py

# Test with a mock submission
python daemon.py status

# Run in AI mode (no mock)
python daemon.py run --no-mock
```

## Alternative: Test Without CLI (Mock Mode)

While waiting for CLI installation, you can test the grading workflow using mock mode:

```powershell
conda activate grader

# Add a test submission
python daemon.py add test_user github "https://github.com/octocat/Hello-World"

# Grade in mock mode (no AI, uses templates)
python daemon.py grade <submission_id>

# View grading results
python daemon.py status

# Check generated feedback
cat submissions/test_user/grading.md
```

Mock mode works **without** the Copilot CLI and demonstrates the full workflow.

## Troubleshooting

### "npm not found"
- Node.js is not installed or not in PATH
- Solution: Install Node.js, then restart PowerShell

### "copilot not found"
- Copilot CLI not installed
- Solution: Run `npm install -g @github/copilot`

### "Authentication required"
- Not logged in to GitHub Copilot
- Solution: Run `copilot` then `/login`, or set `GITHUB_TOKEN` env var

### "Permission denied" during npm install
- Installing to system directory without admin rights
- Solution: Use `npm config set prefix ~/.npm-global` then add to PATH

## What Gets Installed

### Node.js (~50 MB)
- JavaScript runtime
- Includes npm (package manager)
- Required for any npm packages

### @github/copilot (~10 MB)
- The actual Copilot CLI binary
- Written in TypeScript/JavaScript
- Runs on Node.js
- Latest version: v0.0.400 (as of Jan 31, 2026)

### Total Disk Space
- ~60 MB for Node.js + Copilot CLI

## Why Not Include CLI in Python Package?

The Copilot CLI is:
1. **Platform-specific** - Different binaries for Windows/macOS/Linux
2. **Frequently updated** - New releases every few days
3. **GitHub-maintained** - Separate release cycle from SDK
4. **OAuth-dependent** - Needs GitHub authentication separate from Python

This separation allows:
- Python SDK updates without CLI changes
- CLI updates without breaking SDK
- Shared CLI across multiple language SDKs (Python, TypeScript, etc.)

## Current Project Status

Your grading agent is **fully functional** in mock mode:
- ✅ Canvas integration working
- ✅ GitHub repo fetching working
- ✅ State management working
- ✅ Prompt system working
- ✅ Feedback generation working (template-based)

The **only missing piece** is the Copilot CLI for AI-powered grading instead of template-based grading.

## Summary

**To unlock AI grading**, you need to:
1. Install Node.js (via conda, download, or Chocolatey with admin)
2. Install Copilot CLI via npm: `npm install -g @github/copilot`
3. Authenticate: `copilot` → `/login`
4. Run: `python daemon.py run --no-mock`

**Until then**, mock mode provides a complete grading workflow without AI.
