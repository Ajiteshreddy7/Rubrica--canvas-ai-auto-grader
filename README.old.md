# Canvas Auto-Grading Agent 🤖

An intelligent CLI daemon that automatically grades Canvas submissions using **GitHub Copilot SDK**.

Built with a **prompt-first architecture** - intelligence lives in markdown prompt files, Python provides thin wrappers.

## ✨ Features

- **🔄 Auto-Polling**: Checks Canvas every 5 minutes for new submissions
- **🎯 One-Per-Cycle**: Processes exactly one submission per cycle (Ralph-inspired)
- **🤖 AI-Powered**: Uses GitHub Copilot SDK with OAuth authentication
- **📝 Prompt-First**: All grading logic lives in editable markdown files
- **🎨 Rich CLI**: Colored terminal output with status tables and progress indicators
- **💾 State Management**: Persistent JSON-based state tracking
- **🔌 Mock Mode**: Test without Copilot CLI (perfect for development)
- **📊 Multiple Formats**: Supports GitHub repos (structure only), PDFs, text, URLs

## ⚡ Quick Start

### 1. Setup Python Environment

```bash
# Create conda environment (Python 3.11+ required for Copilot SDK)
conda create -n grader python=3.11 -y
conda activate grader

# Install Python dependencies
pip install -r requirements.txt
```

**Why Python 3.11?** The GitHub Copilot SDK requires Python 3.9+ for modern typing features (`typing.Callable[...]` subscripting).

### 2. Setup GitHub Copilot CLI

The Copilot SDK requires the Copilot CLI binary. Choose one method:

#### Option A: Automated Setup (Recommended)
```bash
python setup_copilot.py
```

This interactive script will:
- Check if Node.js/npm are installed
- Install `@github/copilot` npm package globally
- Guide you through authentication (`copilot auth login`)
- Verify everything is working

#### Option B: Manual Setup
```bash
# Install Copilot CLI globally
npm install -g @github/copilot

# Authenticate with GitHub
copilot auth login

# Verify installation
copilot --version
```

**Don't have Node.js?** Download from [nodejs.org](https://nodejs.org/) (LTS version recommended).

### 3. Configure Canvas

Edit `config.json` with your Canvas API credentials:

```json
{
  "canvas": {
    "base_url": "https://uncc.instructure.com",
    "api_token": "YOUR_CANVAS_API_TOKEN_HERE",
    "course_id": "260178",
    "assignment_id": "2772299"
  },
  "github": {
    "token": "YOUR_GITHUB_TOKEN_HERE"
  }
}
```

**Get Canvas API Token:**
1. Go to Canvas → Account → Settings
2. Scroll to "Approved Integrations"
3. Click "+ New Access Token"
4. Copy the generated token

### 4. Initialize Assignment

```bash
python daemon.py init --assignment "Hands-on L2: Basics of GitHub" --max-points 1
```

This creates `status.json` with assignment metadata and initializes the submissions tracker.

### 5. Customize Rubric (Optional)

Edit `rubric.md` with your grading criteria:

```markdown
# Grading Rubric

## Criterion 1: Repository Structure (40%)
- Proper README.md file (20%)
- Clear project organization (10%)
- Appropriate .gitignore (10%)

## Criterion 2: Code Quality (40%)
- Clean, readable code (20%)
- Proper naming conventions (10%)
- Comments where appropriate (10%)

## Criterion 3: Commit History (20%)
- Multiple meaningful commits (15%)
- Clear commit messages (5%)
```

### 6. Run the Grading Agent

```bash
# Test with mock mode (no Copilot needed, generates basic feedback)
python daemon.py run

# Use real AI grading with Copilot
python daemon.py run --no-mock
```

Press `Ctrl+C` to stop gracefully (finishes current operation first).

## 📖 CLI Commands

### Core Commands

```bash
# Start the daemon (polls Canvas, grades one submission per 5-min cycle)
python daemon.py run [--no-mock]

# Show all submissions with status summary
python daemon.py status

# Manually grade a specific submission
python daemon.py grade <submission_id> [--no-mock]

# Reset a failed submission to pending
python daemon.py retry <submission_id>

# Check Copilot authentication status
python daemon.py auth
```

### Setup Commands

```bash
# Initialize assignment configuration
python daemon.py init --assignment "Assignment Name" --max-points 100

# Add a test submission manually
python daemon.py add <student_name> <type> <url>
# Types: github, pdf, text, url
# Example: python daemon.py add john_doe github "https://github.com/user/repo"
```

## 🏗️ Project Structure

```
nerw/
├── daemon.py           # CLI daemon entry point (click-based)
├── grader.py          # Core grading logic (Copilot SDK + mock)
├── canvas.py          # Canvas LMS API client
├── github.py          # GitHub repo structure fetcher (no cloning)
├── state.py           # State management (status.json CRUD)
├── setup_copilot.py   # Interactive Copilot CLI setup script
│
├── config.json        # API credentials (Canvas, GitHub)
├── status.json        # Submission tracker (pending/grading/graded/failed)
├── rubric.md          # Grading rubric markdown
├── requirements.txt   # Python dependencies
│
├── prompts/           # Intelligence lives here (prompt-first)
│   ├── system.md      # AI persona & core values
│   ├── grading.md     # Step-by-step grading workflow
│   └── feedback.md    # Tone guide & phrase templates
│
└── submissions/       # Generated grading files
    └── <student>/
        └── grading.md  # AI-generated feedback with metadata
```

## 🎯 How It Works

### Prompt-First Architecture

All grading intelligence lives in **markdown prompt files**:

1. **`prompts/system.md`** - Defines the AI persona:
   - Core values (clarity, constructive feedback, encouragement)
   - Tone guidelines (supportive TA, not harsh grader)

2. **`prompts/grading.md`** - Step-by-step workflow:
   - Template variables: `{rubric}`, `{submission_content}`, `{assignment_name}`, etc.
   - Structured grading process (analyze → evaluate → feedback → save)

3. **`prompts/feedback.md`** - Tone and phrasing:
   - Constructive phrases ("Great start", "Consider exploring")
   - Encouraging templates ("You're on the right track")

**Why Prompt-First?**
- Non-engineers can customize grading behavior
- Version control for grading logic
- Easy A/B testing of different approaches
- No code changes needed for pedagogical adjustments

### Grading Flow

```
Canvas → Poll → Stage → Queue → Grade → Save → Mark Complete
  ↓        5min    ↓        ↓       ↓       ↓         ↓
 New     Daemon   Add to  Next   Copilot  grading.md State
Subs            status   Pending  SDK               Transition
                 .json
```

1. **Daemon polls Canvas** (every 5 minutes)
2. **New submissions staged** to `status.json` with "pending" status
3. **One submission graded per cycle** (prevents overload)
4. **Copilot SDK processes** with custom grading tool
5. **Feedback saved** to `submissions/<student>/grading.md`
6. **State updated** to "graded" with score/timestamp

### Copilot SDK Integration

The grading agent uses **GitHub Copilot SDK with OAuth authentication**:

```python
# grader.py (simplified)
from copilot import CopilotClient
from copilot.tools import define_tool
from pydantic import BaseModel, Field

# Define the grading tool
@define_tool(description="Save grading results")
async def save_grading(params: GradingParams) -> str:
    # Save score and feedback
    return "Grading saved successfully"

# Create client (uses OAuth automatically)
client = CopilotClient({"auto_start": True})
await client.start()

# Check authentication
auth = await client.get_auth_status()
assert auth.is_authenticated

# Create session with grading tool
session = await client.create_session({
    "model": "gpt-4.1",
    "tools": [save_grading],
    "system_message": {"content": grading_prompts}
})

# Grade the submission
await session.send({"prompt": "Grade this submission..."})
```

**Key Features:**
- **OAuth-based** - No API keys needed, uses `copilot auth login`
- **Tool-based** - Grading results captured via Pydantic-validated tools
- **Async/await** - Proper async handling throughout
- **Event-driven** - Listens for session.idle to know when grading completes

## 🔧 Configuration

### Canvas Setup

Your Canvas course URL contains the IDs you need:
```
https://uncc.instructure.com/courses/260178/assignments/2772299
                                        ^^^^^^           ^^^^^^^
                                      course_id      assignment_id
```

### Environment Variables (Optional)

```bash
# Point to custom Copilot CLI location
export COPILOT_CLI_PATH="/path/to/copilot-cli"

# Use GitHub token for authentication (alternative to OAuth)
export GITHUB_TOKEN="ghp_your_token_here"
```

### Mock vs Real Copilot

**Mock Mode** (`--mock` or default):
- Uses template-based feedback generation
- No Copilot CLI required
- Perfect for testing and development
- Generates basic, structured feedback
- Score: randomized based on submission type

**Copilot Mode** (`--no-mock`):
- Uses full Copilot AI intelligence
- Requires Copilot CLI + authentication
- Analyzes submissions deeply
- Generates personalized, context-aware feedback
- Score: based on actual rubric evaluation

## 📝 Customization

### Change Grading Tone

Edit `prompts/system.md`:
```markdown
# System Prompt

You are a supportive teaching assistant grading...

## Core Values
1. **Clarity First** - Explain concepts simply
2. **Constructive Always** - Focus on learning opportunities
3. **Encouraging** - Recognize effort and progress
...
```

### Adjust Workflow Steps

Edit `prompts/grading.md`:
```markdown
## Step 1: Initial Analysis
First, carefully review the submission content:
- What did the student submit?
- Does it match the assignment requirements?
...

## Step 2: Rubric Evaluation
Evaluate against each criterion:
- {rubric}
...
```

### Modify Rubric

Edit `rubric.md`:
```markdown
# Grading Rubric

## Repository Structure (50%)
- Valid GitHub repository link (25%)
- README.md present (15%)
- At least 3 commits (10%)

## Code Quality (50%)
- Code runs without errors (30%)
- Proper formatting (10%)
- Meaningful variable names (10%)
```

## 🐛 Troubleshooting

### "CLI not found" or "copilot: command not found"

**Solution:**
```bash
# Run the setup script
python setup_copilot.py

# Or manually install
npm install -g @github/copilot

# Verify PATH includes npm global bin
npm config get prefix
# Add to PATH: <prefix>/bin (Unix) or <prefix> (Windows)
```

### "Not authenticated with Copilot"

**Solution:**
```bash
# Authenticate
copilot auth login

# Verify
copilot auth status

# Check from agent
python daemon.py auth
```

### "Python 3.8 incompatible with Copilot SDK"

**Solution:**
```bash
# Create Python 3.11 environment
conda create -n grader python=3.11 -y
conda activate grader
pip install -r requirements.txt
```

The Copilot SDK requires Python 3.9+ for `typing.Callable[...]` subscripting.

### Canvas API 401 Unauthorized

**Solution:**
1. Generate new Canvas API token (Account → Settings → New Access Token)
2. Update `config.json` with the new token
3. Ensure token has proper permissions

### Mock Mode Works, Real Mode Fails

**Checklist:**
1. ✅ Copilot CLI installed? `copilot --version`
2. ✅ Authenticated? `copilot auth status`
3. ✅ Python 3.11+? `python --version`
4. ✅ SDK installed? `pip list | grep github-copilot-sdk`

## 📚 Dependencies

### Python Packages
```
click>=8.0.0         # CLI framework
rich>=13.0.0         # Colored terminal output
requests>=2.28.0     # HTTP client (Canvas/GitHub APIs)
pydantic>=2.0.0      # Data validation (Copilot SDK tools)
github-copilot-sdk>=0.1.0  # GitHub Copilot SDK
PyPDF2>=3.0.0        # PDF text extraction
python-dotenv>=1.0.0 # Environment variable management
```

### External Dependencies
- **Node.js 18+** & **npm** (for Copilot CLI)
- **@github/copilot** (npm package, installed via `setup_copilot.py`)
- **GitHub Copilot subscription** (required for AI grading)

## 🚀 Advanced Usage

### Batch Grading

```bash
# Grade all pending submissions (one per cycle, stops when queue empty)
python daemon.py run --no-mock

# Or manually grade specific submissions
for id in sub_123 sub_456 sub_789; do
    python daemon.py grade $id --no-mock
done
```

### Custom Polling Interval

Edit `daemon.py`:
```python
POLL_INTERVAL = 300  # Change from 5 minutes to desired seconds
```

### Integration with Canvas API

The agent can post grades back to Canvas (currently disabled):

Edit `canvas.py` to add:
```python
def post_grade(submission_id, score, comment):
    """Post grade back to Canvas via API."""
    # Implementation details...
```

### Export Grading Reports

```bash
# All grading markdown files are in submissions/
find submissions -name "grading.md" -exec cat {} \;

# Or generate CSV summary
python -c "
import json
status = json.load(open('status.json'))
for sub in status['submissions']:
    if sub['status'] == 'graded':
        print(f\"{sub['student']},{sub['score']}\")
"
```

## 🤝 Contributing

This is a teaching assistant tool built for UNCC courses. Feel free to fork and adapt for your own institution.

**Key Extension Points:**
- `prompts/*.md` - Customize AI behavior
- `rubric.md` - Define grading criteria
- `grader.py::get_submission_content()` - Add new submission types
- `daemon.py` - Add new CLI commands

## 📄 License

MIT License - Feel free to adapt for your educational needs.

## 🙏 Acknowledgments

- **Ralph (snarktank/ralph)** - Inspired the one-per-cycle polling pattern
- **GitHub Copilot SDK** - Powers the AI grading intelligence
- **Canvas LMS** - Submission management system
- **UNCC** - Testing ground for this educational tool

---

Built with ❤️ for educators who want to spend less time grading and more time teaching.
