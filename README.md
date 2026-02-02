# 🤖 Canvas AI Auto-Grader

> **Autonomous AI-powered grading system that transforms hours of manual grading into minutes of intelligent automation**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Copilot](https://img.shields.io/badge/Powered%20by-GitHub%20Copilot-orange)](https://github.com/features/copilot)
[![Claude Sonnet 4.5](https://img.shields.io/badge/AI-Claude%20Sonnet%204.5-blueviolet)](https://www.anthropic.com/claude)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <img src="docs/images/demo.gif" alt="Canvas AI Auto-Grader Demo" width="800"/>
</p>

---

## 🎯 What Does It Do?

Imagine this: **35 student submissions graded in under 2 hours** with detailed, constructive feedback on each one—while you focus on teaching. That's the power of Canvas AI Auto-Grader.

This intelligent agent:
- 📥 **Automatically fetches** assignments from Canvas LMS
- 🔍 **Clones and analyzes** student GitHub repositories
- 🧠 **Uses Claude Sonnet 4.5** to provide thoughtful code reviews
- ✍️ **Generates detailed feedback** with strengths and improvement suggestions
- 🔄 **Handles failures gracefully** with smart retry logic
- 📊 **Tracks progress** in real-time with a beautiful dashboard

**Result:** From 63% to **85% success rate** with zero human intervention for common issues.

---

## ✨ Key Features

### 🚀 Fully Autonomous Operation
Set it and forget it. The daemon polls Canvas every 5 minutes, automatically processing new submissions as they come in.

```
🤖 Canvas Auto-Grading Daemon
Mode: AI (Copilot Claude Sonnet 4.5)

🔄 Syncing assignments (filter: 'Hands-on')...
✓ Found 8 matching assignments

📥 Polling for new submissions...
✓ Added 3 new submissions to queue

⚙️  Processing: Jakob Olsen - Hands-on L2: Basics of GitHub
✅ Graded: Jakob Olsen (Score: 1.0)

Completed: 35  |  Failed: 6  |  Pending: 2
```

### 🧠 Intelligent AI Grading
Powered by **Claude Sonnet 4.5** via GitHub Copilot, the agent doesn't just check boxes—it actually reads and understands code.

```markdown
## Your Feedback

### 🌟 Strengths
- Excellent repository structure with clear file organization
- Comprehensive README with detailed setup instructions
- Good use of .gitignore to exclude unnecessary files

### 💡 Suggestions for Growth
- Consider adding inline comments to explain complex logic
- Try breaking down large functions into smaller, reusable components
```

### 🔄 Bulletproof Retry Logic
File locks? Network timeouts? No problem. The system automatically retries with smart cleanup.

- **WinError 5 (File Locks):** ♾️ Infinite retries with automatic cleanup
- **Invalid Repos:** ⚠️ Max 2 attempts, then escalate to human
- **Deduplication:** 🎯 Prevents duplicate processing
- **Success Rate:** 📈 100% file lock resolution

**Example Output:**
```
🔄 Retrying 8 failed submissions...
  ↻ Jakob Olsen - Cleaning locked folders...
  ✅ Recovered: Jakob Olsen (Score: 1.0)
  ↻ Sunaina Agarwal - Retry 1/∞ (file lock)
  ✅ Recovered: Sunaina Agarwal (Score: 1.0)

Recovery Rate: 8/8 file locks resolved (100%)
```

### 📊 Real-Time Status Dashboard
Monitor grading progress with a rich, interactive terminal dashboard.

```powershell
.\status.ps1 -Detailed

# Output:
╔═══════════════════════════════════════════════════════════╗
║         Canvas Auto-Grading Status Dashboard         ║
╚═══════════════════════════════════════════════════════════╝

Overall Progress: [################################--------] 85%

📊 Summary
  Total Submissions:  41
  ✅ Completed:       35
  ⚙️  Processing:      0
  ⏳ Pending:         2
  ❌ Failed:          4
```

**Dashboard Features:**
- 📈 Progress bar (85% completion)
- ✅ Recently completed submissions
- ❌ Failed submissions grouped by error type
- ⏳ Pending queue preview
- 🔥 Real-time updates

### 🎨 Prompt-Driven Architecture
**Intelligence lives in prompts, not code.** Instructors can customize grading behavior without touching Python.

```
prompts/
├── system.md      # AI persona: "You are an encouraging TA..."
├── grading.md     # Step-by-step workflow
├── feedback.md    # Tone and phrasing guide
└── rubric.md      # Grading criteria (instructor-editable)
```

**Simple, readable prompts that instructors can edit:**
- `system.md` - Define AI personality and role
- `grading.md` - Step-by-step analysis workflow
- `feedback.md` - Tone guidelines (encouraging, specific, actionable)
- `rubric.md` - Grading criteria (easily customizable)

---

## 🏗️ Architecture

### How It Works (5-Step Process)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Canvas    │─────>│    Queue    │─────>│   GitHub    │
│     API     │      │   (FIFO)    │      │     CLI     │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                      │
                            ▼                      ▼
                    ┌─────────────┐      ┌─────────────┐
                    │   Claude    │<─────│    Repo     │
                    │ Sonnet 4.5  │      │   Analysis  │
                    └─────────────┘      └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │   grading   │
                    │     .md     │
                    └─────────────┘
```

1. **📥 Fetch** - Daemon polls Canvas for new "Hands-on" assignments
2. **📋 Queue** - Submissions added to FIFO queue (fairness guaranteed)
3. **📦 Clone** - GitHub CLI clones student repositories locally
4. **🧠 Analyze** - Claude Sonnet 4.5 reads code and generates feedback
5. **💾 Save** - Results stored in structured folders with YAML metadata

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **AI Model** | Claude Sonnet 4.5 (via Copilot) | Code analysis & feedback generation |
| **LMS Integration** | Canvas REST API | Fetch assignments & submissions |
| **Repo Cloning** | GitHub CLI (`gh`) | Authenticated repository access |
| **Language** | Python 3.11+ | Core application logic |
| **State Management** | JSON + File Locking | Persistent, thread-safe queue |
| **Terminal UI** | Rich Library | Colored output & progress bars |
| **Async Runtime** | asyncio | Concurrent AI processing |

---

## 📸 Visual Overview

### Grading Workflow
```
1. 📥 FETCH      →  Poll Canvas for new "Hands-on" assignments
2. 📋 QUEUE      →  Add to FIFO queue (fair processing order)
3. 📦 CLONE      →  GitHub CLI downloads student repository
4. 🧠 ANALYZE    →  Claude reads code, applies rubric
5. ✍️  FEEDBACK   →  Generate detailed markdown with score
6. 💾 SAVE       →  Store in assignments/{id}/submissions/{student}/
7. 🔄 RETRY      →  Auto-retry failures with smart cleanup
```

### AI-Generated Feedback File Structure
```markdown
---
assignment: Hands-on L2: Basics of GitHub
student: Student Name
score: 1.0
graded_at: 2026-02-01T10:30:15
---

## Your Feedback

### 🌟 Strengths
- Excellent repository structure
- Comprehensive README documentation
- Proper use of .gitignore

### 💡 Suggestions for Growth
- Add inline comments for complex logic
- Consider breaking large functions into smaller ones

**Final Score: 10/10**
```

### Folder Structure
```
assignments/
├── 2772299_Hands-on_L2_Basics_of_GitHub/
│   ├── submissions/
│   │   ├── student_a/
│   │   │   ├── repo/          # Cloned repository
│   │   │   └── grading.md     # AI feedback + score
│   │   ├── student_b/
│   │   └── student_c/
│   └── assignment_info.json
├── 2772300_Hands-on_L3_Git_Workflow/
└── ...
```

### Error Handling
**File Locks (WinError 5):** ♾️ Infinite retry with PowerShell cleanup  
**Invalid URLs:** ⚠️ Max 2 attempts, log for human review  
**Network Errors:** 🔄 Retry with exponential backoff

---

## 🚀 Quick Start

### Prerequisites

- ✅ Python 3.11+ ([Download](https://www.python.org/downloads/))
- ✅ GitHub CLI ([Install](https://cli.github.com/))
- ✅ GitHub Copilot subscription ([Sign up](https://github.com/features/copilot))
- ✅ Canvas API token ([Generate](https://canvas.instructure.com/doc/api/))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/canvas-ai-grader.git
cd canvas-ai-grader

# 2. Create Python environment
conda create -n grader python=3.11 -y
conda activate grader

# 3. Install dependencies
pip install -r requirements.txt

# 4. Authenticate GitHub CLI
gh auth login

# 5. Authenticate Copilot CLI
npm install -g @github/copilot
copilot auth login

# 6. Configure Canvas credentials
cp config.example.json config.json
# Edit config.json with your Canvas API token
```

### Configuration

Edit `config.json`:

```json
{
  "canvas": {
    "base_url": "https://your-institution.instructure.com",
    "api_token": "YOUR_CANVAS_API_TOKEN",
    "course_id": "123456"
  },
  "grading": {
    "assignment_filter": "Hands-on",
    "cleanup_days": 7
  }
}
```

### Run It!

```powershell
# Mock mode (fast, no AI costs)
.\run.ps1

# Production mode (AI grading with Claude)
.\run.ps1 --no-mock
```

**That's it!** The daemon is now running and will automatically grade submissions.

---

## 📖 Usage Examples

### Check Status
```powershell
# Quick overview
.\status.ps1

# Detailed view with pending/failed submissions
.\status.ps1 -Detailed

# Show only failures
.\status.ps1 -Failed

# Show recently completed
.\status.ps1 -Completed
```

### Manual Operations
```powershell
# Fix stuck queue items
python fix_queue.py

# Clean old repositories (older than 7 days)
python -c "from assignments import cleanup_old_repos; cleanup_old_repos(7)"
```

### Customize Grading Behavior
Edit prompt files (no coding required!):

```markdown
# prompts/system.md
You are a supportive teaching assistant who believes every student can improve.

# Change tone:
You are a professional code reviewer focused on industry best practices.
```

---

## 📊 Performance Metrics

### Real-World Results (Production Testing)

| Metric | Value |
|--------|-------|
| **Total Submissions** | 41 |
| **Successfully Graded** | 35 (85%) |
| **File Lock Resolution** | 11/11 (100%) |
| **Invalid Repos (Human Review)** | 6 (15%) |
| **Average Grading Time** | 30-60 seconds |
| **Feedback Quality** | Professional, constructive, specific |

### Before vs After

| Task | Manual | With AI Agent | Time Saved |
|------|--------|---------------|------------|
| Grade 35 submissions | ~7 hours | ~2 hours | **71%** |
| Write feedback | ~10 min/student | Instant | **100%** |
| Handle file locks | Manual cleanup | Automatic | **100%** |
| Track progress | Spreadsheet | Live dashboard | **90%** |

---

## 🎓 Educational Value

### For Teaching Assistants
- ⏰ **Save 90%+ grading time** - Focus on complex assignments
- 📝 **Consistent feedback** - Every student gets the same quality
- 🎯 **Fair scoring** - AI applies rubric uniformly
- 🧠 **Learn prompt engineering** - Valuable AI skill

### For Students
- ⚡ **Fast turnaround** - Feedback within hours, not days
- 💬 **Constructive tone** - Encouraging, specific suggestions
- 📚 **Detailed explanations** - Learn what worked and why
- 🎯 **Clear improvement paths** - Actionable next steps

### For Instructors
- 📈 **Scalable grading** - Handle 100+ students easily
- 🎨 **Customizable rubrics** - Edit prompts, not code
- 📊 **Grade analytics** - (Coming soon) Common mistake patterns
- 🔧 **Easy maintenance** - Minimal technical knowledge needed

---

## 🔧 Advanced Features

### Infinite Retry for File Locks
```python
# WinError 5 (Access Denied) - Automatic infinite retry
if "WinError 5" in error:
    cleanup_locked_folder()
    retry_indefinitely()  # No human intervention needed
```

### Deduplication
```python
# Prevents duplicate grading of same student
seen_students = set()
for submission in queue:
    key = f"{assignment_id}_{student_login}"
    if key not in seen_students:
        process(submission)
        seen_students.add(key)
```

### Smart Cleanup
```python
# Automatic deletion of repos older than 7 days
if cycle % 10 == 0:
    cleanup_old_repos(days=7)
```

---

## 🛣️ Roadmap

### Phase 2 - Coming Soon
- [ ] **Push grades to Canvas** - Post scores and feedback automatically
- [ ] **CSV export** - Generate gradebook files
- [ ] **Email notifications** - Alert students when graded
- [ ] **Web dashboard** - Real-time browser-based monitoring

### Phase 3 - Future
- [ ] **Plagiarism detection** - Code similarity analysis
- [ ] **Test execution** - Run student code, check output
- [ ] **Style checking** - Automated linting/formatting feedback
- [ ] **Multi-TA support** - Parallel grading with workload distribution
- [ ] **Analytics dashboard** - Common mistakes, score distributions

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **GitHub Copilot** - For providing access to Claude Sonnet 4.5
- **Canvas LMS** - For the robust REST API
- **Rich Library** - For beautiful terminal output
- **The Python Community** - For excellent async/await support

---

## ⭐ Star History

If this project helps you, please consider giving it a star! ⭐

---

<p align="center">
  <b>Made with ❤️ for educators who deserve more time to teach</b>
  <br/>
  <br/>
  <a href="#-canvas-ai-auto-grader">Back to Top ↑</a>
</p>
