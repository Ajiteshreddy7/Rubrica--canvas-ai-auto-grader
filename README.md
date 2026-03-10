# Rubrica

**An autonomous grading pipeline that polls Canvas LMS, clones student GitHub repos, and grades submissions with AI -- turning hours of manual review into minutes.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude Sonnet 4.5](https://img.shields.io/badge/AI-Claude%20Sonnet%204.5-blueviolet)](https://www.anthropic.com/claude)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Dashboard](https://img.shields.io/badge/Dashboard-GitHub%20Pages-orange)](https://ajiteshreddy7.github.io/Rubrica--canvas-ai-auto-grader/)

<p align="center">
  <img src="docs/images/demo.gif" alt="Rubrica Demo" width="800"/>
</p>

---

## How It Works

1. **Polls Canvas** for new submissions across all matching assignments
2. **Clones GitHub repos** using authenticated GitHub CLI
3. **Grades with Claude Sonnet 4.5** via GitHub Copilot SDK, applying per-assignment rubrics
4. **Saves structured feedback** as markdown with YAML frontmatter
5. **Posts grades back to Canvas** with comments (optional)
6. **Auto-publishes analytics** to [GitHub Pages](https://ajiteshreddy7.github.io/Rubrica--canvas-ai-auto-grader/)

The pipeline is fault-tolerant with automatic retries, deduplication, and graceful shutdown.

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

| Decision | Rationale |
|----------|-----------|
| FIFO queue persisted to JSON | Crash-recoverable, no DB dependency |
| Rubrics from Canvas API | Auto-pulled, not hardcoded |
| Prompt-driven grading (markdown) | Instructors customize without touching code |
| Async daemon + graceful shutdown | Finishes current grading on SIGINT |
| Git-plumbing publish | Updates gh-pages without touching working tree |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Engine | Claude Sonnet 4.5 (GitHub Copilot SDK) |
| LMS | Canvas REST API (paginated) |
| Repo Cloning | GitHub CLI (`gh`) |
| Config | Pydantic v2 |
| CLI | Click + Rich |
| Queue | JSON + threading.Lock |
| Analytics | Chart.js (self-contained HTML) |

---

## CLI

```
$ python cli.py --help

Commands:
  run        Start the grading daemon
  grade      Interactive one-shot grading (select assignments & students)
  status     Show queue status (pending/completed/failed)
  analytics  Score distributions, student rankings, HTML reports
  export     Export all grades to CSV
  publish    Publish analytics dashboard to GitHub Pages
  retry      Retry eligible failed submissions
  fix-queue  Repair stuck queue items after a crash
```

**Quick examples:**
```bash
python cli.py run                                              # daemon (mock mode)
python cli.py run --no-mock                                    # daemon (real AI)
python cli.py grade -a "Hands-on L6" --all-students --no-mock -y  # one-shot grade
python cli.py analytics --html                                 # HTML report
python cli.py publish                                          # push dashboard to Pages
python cli.py status --detailed                                # queue overview
python cli.py export -o grades.csv                             # CSV export
```

### AI-Generated Feedback

Each submission produces a `grading.md` with YAML frontmatter:

```markdown
---
student: Jack Karegeannes
assignment_title: Assignment #1 - Virtualization and Containerization
score: 3.0
submission_type: github
---
# Grading Report

## Strengths
- Excellent repository structure with clear file organization
- Comprehensive README with detailed setup instructions

## Suggestions for Growth
- Consider adding inline comments to explain complex logic
```

Grading behavior is controlled by editable prompt files (`prompts/system.md`, `grading.md`, `feedback.md`) -- no code changes needed. Per-assignment rubrics are auto-pulled from Canvas.

---

## Project Structure

```
rubrica/
  cli.py               -- Click CLI entry point
  daemon_new.py         -- Async daemon loop (poll -> queue -> grade -> retry)
  canvas.py             -- Canvas API client
  grader_new.py         -- AI grading via GitHub Copilot SDK
  analytics.py          -- Score computation engine
  report_generator.py   -- HTML report with Chart.js
  publish.py            -- Git-plumbing publisher for GitHub Pages
  submission_queue.py   -- Thread-safe FIFO queue (JSON persistence)
  assignments.py        -- Folder structure and grading result storage
  repo_cloner.py        -- GitHub CLI wrapper
  config.py             -- Pydantic config models
  logger.py             -- Rotating file logger
  fix_queue.py          -- Queue repair utility
  prompts/              -- Editable AI prompt files
  config.json           -- Credentials and settings (gitignored)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (`gh auth login`)
- [GitHub Copilot](https://github.com/features/copilot) subscription
- Canvas LMS API token

### Installation

```bash
git clone https://github.com/Ajiteshreddy7/Rubrica--canvas-ai-auto-grader.git
cd Rubrica--canvas-ai-auto-grader
pip install -r requirements.txt
gh auth login
```

### Configuration

Create `config.json`:

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

---

## Roadmap

- [x] Canvas API integration (assignments, submissions, rubrics)
- [x] FIFO queue with crash recovery
- [x] AI grading with Claude Sonnet 4.5
- [x] Automatic retry with smart cleanup
- [x] Post grades back to Canvas
- [x] Score analytics (terminal + HTML + JSON)
- [x] Selective grading (`grade` command)
- [x] Auto-publish dashboard to GitHub Pages
- [ ] Plagiarism detection (code similarity)
- [ ] Student code execution and test validation
- [ ] Multi-TA parallel grading

---

## License

MIT License. See [LICENSE](LICENSE) for details.
