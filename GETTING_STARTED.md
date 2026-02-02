# Getting Started Guide 🚀

Complete step-by-step setup guide for the Canvas Auto-Grading Agent.

## Prerequisites Check

Before starting, make sure you have:
- [x] Python 3.11+ (required for Copilot SDK)
- [x] Conda (or virtualenv for environment management)
- [ ] Node.js 18+ & npm (optional, only for Copilot mode)
- [ ] GitHub Copilot subscription (optional, only for AI grading)
- [x] Canvas LMS access with API permissions
- [ ] GitHub account (for Copilot authentication)

## Setup Steps

### Step 1: Python Environment Setup

```bash
# Check Python version (must be 3.11+)
python --version

# Create conda environment
conda create -n grader python=3.11 -y

# Activate environment
conda activate grader

# Install all Python dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "click|rich|pydantic|copilot"
```

**Expected Output:**
```
click            8.1.7
rich             13.7.0
pydantic         2.5.3
github-copilot-sdk 0.1.20
```

### Step 2: Verify Core Dependencies

```bash
python verify_deps.py
```

This will show a detailed status of all dependencies. At minimum, you need:
- ✓ Python Version: 3.11+
- ✓ All Python packages
- ✓ Config files (config.json, status.json, rubric.md, prompts/*.md)
- ✓ Canvas Configuration

**Mock Mode Ready**: If you see these checkmarks, you can run in mock mode immediately!

### Step 3: Canvas API Configuration

#### Get Your Canvas API Token

1. Log in to Canvas (https://uncc.instructure.com)
2. Go to **Account → Settings**
3. Scroll down to **Approved Integrations**
4. Click **+ New Access Token**
5. Set Purpose: "Grading Agent"
6. Set Expiration: (optional, recommend 90 days)
7. Click **Generate Token**
8. **IMPORTANT**: Copy the token immediately (you won't see it again!)

#### Extract Course and Assignment IDs

Your Canvas URL contains the IDs you need:

```
https://uncc.instructure.com/courses/260178/assignments/2772299
                                        ^^^^^^           ^^^^^^^
                                      course_id      assignment_id
```

#### Update config.json

```json
{
  "canvas": {
    "base_url": "https://uncc.instructure.com",
    "api_token": "YOUR_CANVAS_TOKEN_HERE",
    "course_id": "260178",
    "assignment_id": "2772299"
  },
  "github": {
    "token": ""
  }
}
```

**Verify Configuration:**
```bash
python verify_deps.py
```

You should now see: ✓ Canvas Configuration: Configured

### Step 4: Initialize Assignment

```bash
python daemon.py init --assignment "Hands-on L2: Basics of GitHub" --max-points 1
```

This creates/updates `status.json` with:
- Assignment name
- Maximum points
- Empty submissions array

**Verify:**
```bash
python daemon.py status
```

Expected output:
```
╭─────── Assignment: Hands-on L2: Basics of GitHub (1 points) ───────╮
│ Pending: 0 │ Grading: 0 │ Graded: 0 │ Failed: 0 │
╰─────────────────────────────────────────────────────────────────────╯
```

### Step 5: Test with Mock Mode

Mock mode works **without Copilot CLI** - perfect for testing!

```bash
# Add a test submission
python daemon.py add test_student github "https://github.com/octocat/Hello-World"

# Check status
python daemon.py status

# Grade it manually (mock mode)
python daemon.py grade <submission_id>

# Check generated feedback
cat submissions/test_student/grading.md
```

**Expected Output:**
```
✓  Graded: test_student - 1.0/1
```

The grading.md file will contain:
- YAML metadata (submission_id, student, score, timestamp)
- Mock feedback (structured but basic)

### Step 6: Run Daemon in Mock Mode

```bash
python daemon.py run
```

**What happens:**
- Polls Canvas every 5 minutes (300 seconds)
- Fetches new submissions
- Grades one submission per cycle
- Generates feedback in mock mode
- Colored terminal output with progress

**Stop gracefully:** Press `Ctrl+C` (waits for current operation to finish)

### Step 7: Setup Copilot (Optional - for AI Grading)

If you want **real AI-powered grading**, you need the Copilot CLI:

#### Option A: Automated Setup

```bash
python setup_copilot.py
```

This interactive script will:
1. Check if Node.js/npm are installed
2. Install `@github/copilot` globally via npm
3. Guide you through `copilot auth login`
4. Verify everything works

#### Option B: Manual Setup

```bash
# Install Node.js from https://nodejs.org/ (if not installed)
node --version  # Should be 18+
npm --version

# Install Copilot CLI globally
npm install -g @github/copilot

# Authenticate with GitHub
copilot auth login

# Verify
copilot --version
copilot auth status
```

**Expected Output:**
```
✓ Logged in to github.com as <your-username>
```

#### Verify Copilot Setup

```bash
# Check from Python
python daemon.py auth

# Or full system check
python verify_deps.py
```

You should now see all dependencies as ✓ OK.

### Step 8: Run with Real Copilot AI

```bash
python daemon.py run --no-mock
```

**Differences from Mock Mode:**
- Uses GitHub Copilot AI models (gpt-4.1)
- Analyzes submissions deeply
- Generates personalized, context-aware feedback
- Applies rubric criteria intelligently
- Provides specific, encouraging suggestions

**Test it:**
```bash
# Add a test submission
python daemon.py add john_doe github "https://github.com/torvalds/linux"

# Grade with AI
python daemon.py grade <submission_id> --no-mock

# Compare feedback quality
cat submissions/john_doe/grading.md
```

## Customization

### Change Rubric

Edit `rubric.md`:

```markdown
# Grading Rubric

## Repository Quality (60%)
- Valid GitHub repository link (30%)
- README.md file present (20%)
- At least 3 meaningful commits (10%)

## Code Structure (40%)
- Files properly organized (20%)
- Appropriate .gitignore (10%)
- Clean code formatting (10%)
```

### Adjust AI Persona

Edit `prompts/system.md`:

```markdown
You are a [STRICT/LENIENT/SUPPORTIVE] teaching assistant grading...

## Core Values
1. **[Clarity/Rigor/Encouragement] First** - ...
2. **[Constructive/Detailed/Brief] Always** - ...
```

### Modify Workflow

Edit `prompts/grading.md` to change the step-by-step grading process.

## Troubleshooting

### Issue: "Python 3.8 not compatible"

**Solution:**
```bash
conda create -n grader python=3.11 -y
conda activate grader
pip install -r requirements.txt
```

### Issue: "copilot: command not found"

**Solution:**
```bash
# Check if npm is installed
npm --version

# If not, install Node.js from https://nodejs.org/

# Then install Copilot
npm install -g @github/copilot

# Add npm global bin to PATH
npm config get prefix
# Add <prefix>/bin to your PATH
```

### Issue: "Not authenticated with Copilot"

**Solution:**
```bash
copilot auth login
# Follow the browser authentication flow
```

### Issue: "Canvas API 401 Unauthorized"

**Solutions:**
1. Regenerate Canvas API token (Account → Settings)
2. Ensure token hasn't expired
3. Check base_url matches your institution
4. Verify course_id and assignment_id are correct

### Issue: Mock mode works, Copilot mode fails

**Debug checklist:**
```bash
# 1. Check Python version
python --version  # Must be 3.11+

# 2. Check SDK installation
pip show github-copilot-sdk

# 3. Check CLI installation
copilot --version

# 4. Check authentication
copilot auth status

# 5. Run verification
python verify_deps.py

# 6. Check from daemon
python daemon.py auth
```

## Common Workflows

### Daily TA Workflow

```bash
# Morning: Start daemon
conda activate grader
python daemon.py run --no-mock

# Leave it running (polls every 5 minutes)
# Grades submissions automatically

# Afternoon: Check progress
python daemon.py status

# End of day: Stop daemon
# Press Ctrl+C (gracefully stops after current operation)
```

### Manual Grading Workflow

```bash
# Check pending submissions
python daemon.py status

# Grade specific submissions
python daemon.py grade sub_123 --no-mock
python daemon.py grade sub_456 --no-mock

# Retry failed submissions
python daemon.py retry sub_789
```

### Bulk Processing

```bash
# Let daemon grade all pending submissions
# (One per cycle until queue is empty)
python daemon.py run --no-mock

# Monitor in real-time
watch -n 30 'python daemon.py status'
```

## Next Steps

1. **Test in mock mode first** - Verify everything works
2. **Set up Copilot** - For AI-powered grading
3. **Customize prompts** - Adjust to your teaching style
4. **Update rubric** - Match your grading criteria
5. **Run in production** - Start auto-grading real submissions

## Getting Help

### Check Logs

```bash
# Daemon output is displayed in terminal
# For debugging, check:
cat submissions/<student>/grading.md  # Generated feedback
cat status.json  # Submission states
cat config.json  # Configuration
```

### Verify System State

```bash
python verify_deps.py   # Full dependency check
python daemon.py status # Submission summary
python daemon.py auth   # Copilot authentication
```

### Report Issues

Check these files for debugging:
- `status.json` - Submission states
- `config.json` - Configuration
- `submissions/*/grading.md` - Generated feedback
- Terminal output - Daemon logs

## Performance Notes

- **Polling Interval**: 5 minutes (configurable in `daemon.py`)
- **Rate Limiting**: One submission per cycle (prevents API overload)
- **Timeout**: 2 minutes per grading operation
- **Concurrent Sessions**: One Copilot session at a time
- **State Persistence**: JSON-based (survives restarts)

## Security Considerations

1. **API Tokens**: Keep `config.json` out of version control (.gitignore it)
2. **Copilot Auth**: Uses OAuth (more secure than API keys)
3. **Student Data**: `submissions/` contains feedback (be careful sharing)
4. **GitHub Tokens**: Optional, only for private repo access

## Success Indicators

You're ready to go when:
- [x] `verify_deps.py` shows all critical dependencies as ✓
- [x] Mock grading works: `python daemon.py run`
- [x] Test submission generates feedback
- [x] Copilot authentication succeeds (if using AI mode)
- [x] Daemon can poll Canvas without errors

---

**Need Help?** Run `python verify_deps.py` for a comprehensive system check!
