# Rubrica

**An autonomous grading pipeline that polls Canvas LMS, clones student GitHub repos, and grades submissions with AI -- turning hours of manual review into minutes.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude Sonnet 4.5](https://img.shields.io/badge/AI-Claude%20Sonnet%204.5-blueviolet)](https://www.anthropic.com/claude)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <img src="docs/images/demo.gif" alt="Rubrica Demo" width="800"/>
</p>

---

## The Problem

Grading programming assignments is repetitive, time-consuming, and inconsistent. A TA grading 30 GitHub submissions manually spends ~7 hours reading code, writing feedback, and entering scores -- and the 30th student gets different quality feedback than the 1st.

## The Solution

This system runs as a background daemon that:

1. **Polls Canvas** for new submissions across all matching assignments
2. **Clones GitHub repos** using authenticated GitHub CLI
3. **Grades with Claude Sonnet 4.5** via GitHub Copilot SDK, applying per-assignment rubrics
4. **Saves structured feedback** as markdown with YAML frontmatter
5. **Posts grades back to Canvas** with comments (optional)
6. **Generates analytics** -- score distributions, student rankings, common mistake patterns

The entire pipeline is fault-tolerant with automatic retries, deduplication, and graceful shutdown.

---

## Architecture

```
                          Canvas LMS API
                               |
                    +----------+----------+
                    |                     |
              Fetch Assignments    Fetch Submissions
                    |                     |
                    v                     v
             +-------------+    +-----------------+
             | assignment  |    |  FIFO Queue     |
             | .json +     |    |  (queue.json)   |
             | rubric.md   |    +--------+--------+
             +-------------+             |
                                         v
                                 +-------+--------+
                                 |  Clone Repo    |
                                 |  (GitHub CLI)  |
                                 +-------+--------+
                                         |
                                         v
                                 +-------+--------+
                                 | Claude Sonnet  |
                                 | 4.5 via        |
                                 | Copilot SDK    |
                                 +-------+--------+
                                         |
                          +--------------+--------------+
                          |              |              |
                          v              v              v
                     grading.md    Post Grade     Analytics
                     (feedback)    to Canvas      Dashboard
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FIFO queue persisted to JSON** | Survives crashes; no database dependency; human-readable state |
| **Per-assignment rubrics from Canvas API** | Rubric criteria pulled automatically, not hardcoded |
| **Prompt-driven grading (markdown files)** | Instructors customize AI behavior without touching Python |
| **Pydantic config validation** | Fail fast on misconfiguration instead of silent errors at runtime |
| **Async daemon with graceful shutdown** | SIGINT/SIGTERM handlers finish current grading before exit |
| **Thread-locked queue operations** | Prevents race conditions during concurrent file access |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| AI Engine | Claude Sonnet 4.5 (GitHub Copilot SDK) | Best-in-class code understanding and feedback generation |
| LMS Integration | Canvas REST API (paginated) | Full assignment/submission/rubric lifecycle management |
| Repo Cloning | GitHub CLI (`gh`) | Handles auth, private repos, and rate limiting |
| Config | Pydantic v2 models | Type-safe validation with clear error messages |
| CLI | Click + Rich | Professional terminal UX with colored output and tables |
| Queue | JSON file + threading.Lock | Zero-dependency, crash-recoverable persistence |
| Analytics | Chart.js (embedded HTML) | Self-contained reports, no server needed |
| Logging | RotatingFileHandler | 5MB rotation, 5 backups, structured log format |

---

## Features

### Autonomous Daemon

The daemon runs continuously, polling Canvas at configurable intervals:

```
$ python cli.py run

Rubrica
Mode: AI

>> Syncing assignments (filter: '['Hands-on', 'Assignment']')...
[OK] Found 11 matching assignments

>> Polling for new submissions...
[OK] Added 161 new submissions to queue

> Processing: Jack Karegeannes - Assignment #1 - Virtualization and Containerization
  > Cloning repository...
  [OK] Cloned successfully
  > Grading...
  [OK] Graded: 3.0/3.0
```

### CLI Interface

```
$ python cli.py --help

Commands:
  run        Start the grading daemon
  grade      Interactive one-shot grading (select assignments & students)
  status     Show queue status (pending/completed/failed)
  analytics  Score distributions, student rankings, HTML reports
  export     Export all grades to CSV
  retry      Retry eligible failed submissions
  fix-queue  Repair stuck queue items after a crash
```

**Status dashboard:**
```
$ python cli.py status --detailed

+--------------------- Queue Status ----------------------+
| Pending:    75                                          |
| Processing: 0                                           |
| Completed:  43                                          |
| Failed:     5                                           |
+---------------------------------------------------------+
```

### Interactive Grading

The `grade` command lets you pick specific assignments and students to grade in one shot -- no daemon required:

```
$ python cli.py grade

Rubrica - Interactive Grade
Mode: Mock

Fetching assignments from Canvas...

Assignments:
  [1] Assignment #1 - Virtualization and Containerization  (ID: 2772289, 3.0 pts)
  [2] Assignment #2 - Big Data Platforms  (ID: 2772290, 3.0 pts)
  [0] All

Select (comma-separated numbers, or 0 for all): 1

Students for 'Assignment #1 - Virtualization ...' (26 submissions):
  [1] Alice Smith  (github)
  [2] Bob Jones    (github)
  ...
  [0] All

Select: 0
Ready to grade 26 submission(s) across 1 assignment(s).
Proceed? (y/n): y
```

Or skip the menus entirely with CLI flags:

```bash
# Grade a specific assignment, all students, real AI, no confirmation
python cli.py grade -a "Hands-on L6" --all-students --no-mock -y
```

**Analytics:**
```
$ python cli.py analytics

+-------------------- Analytics Overview ---------------------+
| Total Graded:   43                                          |
| Students:       27                                          |
| Assignments:    2                                           |
| Average Score:  100.0%                                      |
| Pass Rate:      100.0%                                      |
+-------------------------------------------------------------+

Submission Types: github: 34 | pdf: 9

Per-Assignment Statistics:
| Assignment                         | N  | Avg Score | Avg %  | Pass Rate |
|------------------------------------+----+-----------+--------+-----------|
| Assignment #1 - Virtualization ... | 26 | 3.0/3.0   | 100.0% | 100.0%    |
| Assignment #2 - Big Data ...       | 17 | 3.0/3.0   | 100.0% | 100.0%    |
```

**HTML report generation:**
```
$ python cli.py analytics --html
HTML report generated: analytics_report.html
```

Generates a self-contained HTML file with Chart.js visualizations: score distribution histograms, assignment comparison charts, submission type breakdown, sortable student performance table, and feedback pattern analysis.

### AI-Generated Feedback

Each submission produces a `grading.md` file with YAML frontmatter:

```markdown
---
submission_id: 128555151
student: Jack Karegeannes
assignment_id: 2772289
assignment_title: Assignment #1 - Virtualization and Containerization
score: 3.0
graded_at: 2026-03-09T16:35:18.276194
submission_type: github
submission_url: https://github.com/Karegeannes/Assignment1-Docker-Containers
---
# Grading Report

**Assignment:** Assignment #1 - Virtualization and Containerization
**Score:** 3.0 / 3.0

## Strengths
- Excellent repository structure with clear file organization
- Comprehensive README with detailed setup instructions
- Good use of .gitignore to exclude unnecessary files

## Suggestions for Growth
- Consider adding inline comments to explain complex logic
- Try breaking down large functions into smaller, reusable components
```

### Prompt-Driven Grading

Grading behavior is controlled by editable markdown files -- no code changes needed:

```
prompts/
  system.md     -- AI persona and role definition
  grading.md    -- Step-by-step analysis workflow
  feedback.md   -- Tone and formatting guidelines
rubric.md       -- Default rubric (fallback)
```

Per-assignment rubrics are automatically pulled from Canvas and saved alongside each assignment. The AI applies the correct rubric for each submission.

### Fault Tolerance

- **WinError 5 (file locks):** Infinite retry with PowerShell-based forced cleanup
- **Clone failures:** Max 1 retry, then flagged for human review
- **Queue corruption:** `fix-queue` command repairs truncated JSON from crashes
- **Deduplication:** Same student+assignment never processed twice
- **Graceful shutdown:** Ctrl+C finishes current grading before exit

---

## Project Structure

```
rubrica/
  cli.py               -- Click CLI entry point (run, status, analytics, export, retry)
  daemon_new.py         -- Async daemon loop (poll -> queue -> grade -> retry)
  canvas.py             -- Canvas API client (assignments, submissions, rubrics, grade posting)
  grader_new.py         -- AI grading via GitHub Copilot SDK
  analytics.py          -- Score computation engine (per-assignment, per-student, patterns)
  report_generator.py   -- Self-contained HTML report with Chart.js
  submission_queue.py   -- Thread-safe FIFO queue with JSON persistence
  assignments.py        -- Folder structure management and grading result storage
  repo_cloner.py        -- GitHub CLI wrapper for repo cloning
  config.py             -- Pydantic config models with validation
  logger.py             -- Rotating file logger
  fix_queue.py          -- Queue repair utility
  prompts/              -- Editable AI prompt files
  rubric.md             -- Default grading rubric
  config.json           -- Canvas credentials and settings (gitignored)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- [GitHub Copilot](https://github.com/features/copilot) subscription
- Canvas LMS API token
- (Recommended) [conda](https://docs.conda.io/) for environment management

### Installation

```bash
git clone https://github.com/yourusername/rubrica.git
cd rubrica

# Create and activate a conda environment (recommended)
conda create -n grader python=3.10 -y
conda activate grader

pip install -r requirements.txt

gh auth login
```

### Configuration

Create `config.json` from the template:

```json
{
  "canvas": {
    "base_url": "https://your-institution.instructure.com/",
    "api_token": "YOUR_CANVAS_API_TOKEN",
    "course_id": "123456"
  },
  "grading": {
    "clone_path": "assignments",
    "cleanup_days": 7,
    "assignment_filter": ["Hands-on", "Assignment"],
    "post_to_canvas": false
  },
  "daemon": {
    "poll_interval_seconds": 300
  }
}
```

| Field | Description |
|-------|-------------|
| `base_url` | Your institution's Canvas URL |
| `api_token` | Generated from Canvas > Settings > Access Tokens |
| `course_id` | Found in the Canvas course URL |
| `assignment_filter` | Only process assignments containing these keywords |
| `post_to_canvas` | Set `true` to automatically post grades and comments |
| `poll_interval_seconds` | Seconds between polling cycles |

### Usage

```bash
# Start daemon in mock mode (no AI costs, for testing)
python cli.py run

# Start daemon with real AI grading
python cli.py run --no-mock

# Scope the daemon to specific assignments
python cli.py run -a "Hands-on" -a "Assignment"

# Interactive grading (pick assignments and students from a menu)
python cli.py grade

# Grade a specific assignment non-interactively
python cli.py grade -a "Hands-on L6" --all-students --no-mock -y

# Check queue status
python cli.py status --detailed

# View analytics in terminal
python cli.py analytics

# Generate HTML analytics report
python cli.py analytics --html

# Export grades to CSV
python cli.py export -o grades.csv

# Filter analytics to one assignment
python cli.py analytics -a "Assignment #1"

# Retry failed submissions
python cli.py retry
```

> **Note:** If you use a conda environment, prefix commands with `conda run -n <env> --no-banner` to ensure the correct Python is used.

---

## Metrics

Tested against a real university course (ITCS 6190, UNC Charlotte):

| Metric | Value |
|--------|-------|
| Assignments synced | 11 |
| Submissions processed | 161 |
| Submissions graded (AI) | 43 (26/26 Hands-on L6 complete) |
| Students | 27 |
| Grading time per submission | 30-60 seconds |
| File lock auto-recovery | 100% |
| Manual intervention required | Clone failures due to Windows path limits only |

---

## Roadmap

- [x] Canvas API integration (assignments, submissions, rubrics)
- [x] FIFO queue with crash recovery
- [x] AI grading with Claude Sonnet 4.5
- [x] Automatic retry with smart cleanup
- [x] CLI with Click (run, status, export, retry, fix-queue)
- [x] Post grades back to Canvas
- [x] Per-assignment rubric pulling from Canvas API
- [x] Score analytics dashboard (terminal + HTML + JSON)
- [x] Feedback pattern analysis
- [x] Centralized config with Pydantic validation
- [x] Rotating file logging
- [x] Selective grading (`grade` command with assignment/student menus)
- [ ] Plagiarism detection (code similarity analysis)
- [ ] Student code execution and test validation
- [ ] Multi-TA parallel grading with workload distribution
- [ ] Web-based real-time monitoring dashboard

---

## License

MIT License. See [LICENSE](LICENSE) for details.
