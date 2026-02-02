# 🚀 GitHub Repository Setup Guide

Follow these steps to create a private GitHub repository for your Canvas AI Auto-Grader project.

---

## Step 1: Create Private Repository

### Option A: Using GitHub Web Interface

1. **Go to GitHub** - https://github.com/new

2. **Repository Details:**
   - **Repository name:** `canvas-ai-auto-grader` (or your preferred name)
   - **Description:** "Autonomous AI-powered grading system using Claude Sonnet 4.5 via GitHub Copilot"
   - **Visibility:** Select **Private** 🔒
   - **Initialize:** 
     - ✅ Add README (we'll replace it)
     - ✅ Add .gitignore (select "Python")
     - ✅ Add license (select "MIT License")

3. **Click "Create repository"**

### Option B: Using GitHub CLI

```bash
# Navigate to your project directory
cd C:\Users\ajite\OneDrive\Desktop\nerw

# Create private repo
gh repo create canvas-ai-auto-grader --private --description "Autonomous AI-powered grading system using Claude Sonnet 4.5 via GitHub Copilot"

# Or create and push immediately
gh repo create canvas-ai-auto-grader --private --source=. --push
```

---

## Step 2: Prepare Your Local Repository

### Clean Sensitive Data

**IMPORTANT:** Remove sensitive information before pushing!

```powershell
# 1. Create a safe config example
Copy-Item config.json config.example.json

# 2. Edit config.example.json to remove sensitive data
# Replace actual values with placeholders:
```

**config.example.json:**
```json
{
  "canvas": {
    "base_url": "https://your-institution.instructure.com",
    "api_token": "YOUR_CANVAS_API_TOKEN_HERE",
    "course_id": "YOUR_COURSE_ID"
  },
  "grading": {
    "clone_path": "assignments",
    "cleanup_days": 7,
    "assignment_filter": "Hands-on"
  },
  "daemon": {
    "poll_interval_seconds": 300
  }
}
```

### Update .gitignore

Make sure these files are ignored:

```bash
# Add to .gitignore
echo "config.json" >> .gitignore
echo "queue.json" >> .gitignore
echo "status.json" >> .gitignore
echo "assignments/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".vscode/" >> .gitignore
echo "*.log" >> .gitignore
echo "README.old.md" >> .gitignore
```

### Remove Tracked Sensitive Files

If you've already committed sensitive files:

```bash
# Remove from Git history (WARNING: This rewrites history)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.json queue.json" \
  --prune-empty --tag-name-filter cat -- --all

# Or use BFG Repo-Cleaner (safer):
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files config.json
```

---

## Step 3: Initial Commit

```bash
# Initialize Git (if not already done)
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: Canvas AI Auto-Grader v1.0

- Autonomous grading daemon with FIFO queue
- AI-powered feedback using Claude Sonnet 4.5
- Infinite retry logic for file locks
- Real-time status dashboard
- 85% success rate on production testing"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/canvas-ai-auto-grader.git

# Push to GitHub
git push -u origin main
```

---

## Step 4: Add Screenshots

After capturing all screenshots (see `docs/SCREENSHOT_GUIDE.md`):

```bash
# Add images
git add docs/images/*.png docs/images/*.gif

# Commit
git commit -m "docs: Add screenshots and demo images"

# Push
git push
```

---

## Step 5: Repository Settings

### Enable Features

1. **Go to:** `https://github.com/YOUR_USERNAME/canvas-ai-auto-grader/settings`

2. **Features to enable:**
   - ✅ **Issues** - For bug tracking
   - ✅ **Discussions** - For community Q&A
   - ✅ **Projects** - For roadmap tracking
   - ✅ **Wiki** - For extended documentation

3. **Security:**
   - Go to **Settings → Security → Dependabot**
   - Enable **Dependabot alerts**
   - Enable **Dependabot security updates**

### Add Topics (Tags)

Under **Settings → About**, add topics:
```
ai, artificial-intelligence, github-copilot, claude, canvas-lms, 
auto-grading, education, teaching-assistant, python, asyncio, 
prompt-engineering, automation
```

### Create Repository Description

**About section:**
```
🤖 Autonomous AI-powered grading system using Claude Sonnet 4.5 via GitHub Copilot. Grades Canvas submissions with 85% success rate and detailed feedback in 30-60 seconds per student.
```

**Website:** (Add if you create a GitHub Pages site)

---

## Step 6: Add Branch Protection (Optional)

If you plan to collaborate:

1. **Go to:** Settings → Branches
2. **Add rule for `main` branch:**
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require conversation resolution before merging

---

## Step 7: Create Releases

### Tag Your First Release

```bash
# Create annotated tag
git tag -a v1.0.0 -m "Release v1.0.0: Production-ready autonomous grading

Features:
- Multi-assignment auto-sync
- AI grading with Claude Sonnet 4.5
- Infinite retry logic for file locks
- Real-time status dashboard
- 85% success rate on 41 submissions"

# Push tag
git push origin v1.0.0
```

### Create Release on GitHub

1. **Go to:** Releases → Draft a new release
2. **Choose tag:** v1.0.0
3. **Title:** "v1.0.0 - Production Release"
4. **Description:**

```markdown
## 🎉 First Production Release!

Canvas AI Auto-Grader is now production-ready after successful testing on 41 real student submissions.

### ✨ Highlights
- **85% success rate** (35/41 submissions automatically graded)
- **100% file lock resolution** (11/11 recovered with infinite retry)
- **30-60 second grading time** per submission
- **Professional AI feedback** using Claude Sonnet 4.5

### 📦 What's Included
- Autonomous daemon with FIFO queue processing
- Canvas LMS integration (auto-fetch assignments)
- GitHub CLI integration (clone student repos)
- AI-powered grading with constructive feedback
- Real-time status dashboard (PowerShell)
- Robust error handling with smart retry logic

### 🚀 Quick Start
See the [README.md](README.md) for installation instructions.

### 📊 Stats from Production Testing
- Total submissions: 41
- Successfully graded: 35 (85%)
- File locks resolved: 11/11 (100%)
- Average time: 30-60 seconds/student
- Time saved: 71% vs manual grading

### 🙏 Acknowledgments
Built with GitHub Copilot, Canvas LMS API, and Python asyncio.
```

5. **Attach files** (optional):
   - requirements.txt
   - config.example.json
   - Screenshot samples

6. **Publish release**

---

## Step 8: Add Additional Files

### Create LICENSE File

If you selected MIT License during creation, it's already there. Otherwise:

**LICENSE:**
```
MIT License

Copyright (c) 2026 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Create CONTRIBUTING.md

```markdown
# Contributing to Canvas AI Auto-Grader

We welcome contributions! Here's how you can help:

## 🐛 Report Bugs
Open an issue with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

## 💡 Suggest Features
Use GitHub Discussions to propose new features.

## 🔧 Submit Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Code Style
- Follow PEP 8 for Python code
- Use type hints
- Add docstrings to functions
- Keep functions small and focused

## ✅ Before Submitting
- Test your changes
- Update documentation
- Add comments for complex logic
```

### Create CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-02-01

### Added
- Initial release
- Autonomous daemon with FIFO queue processing
- Canvas LMS integration for auto-fetching assignments
- GitHub CLI integration for cloning student repos
- AI-powered grading using Claude Sonnet 4.5 via GitHub Copilot
- Infinite retry logic for Windows file locks (WinError 5)
- Real-time status dashboard (PowerShell script)
- Comprehensive error handling and human escalation
- Automatic cleanup of old repositories (7-day retention)
- Prompt-driven architecture (intelligence in Markdown files)

### Stats
- Production tested on 41 real submissions
- 85% success rate (35/41 graded)
- 100% file lock resolution (11/11)
- Average grading time: 30-60 seconds per student
```

---

## Step 9: Enhance Repository Visibility

### Add Social Preview Image

1. **Create a banner image** (1280x640px recommended)
   - Use Canva, Figma, or Photoshop
   - Include: Project name, tagline, key features
   - Example: "Canvas AI Auto-Grader | 85% Success Rate | Claude Sonnet 4.5"

2. **Upload:**
   - Settings → General → Social preview
   - Upload your banner image

### Create GitHub Pages (Optional)

```bash
# Create gh-pages branch
git checkout -b gh-pages

# Add index.html or use README as homepage
echo "# Canvas AI Auto-Grader" > index.md
git add index.md
git commit -m "docs: Create GitHub Pages"
git push origin gh-pages

# Enable in Settings → Pages → Source: gh-pages branch
```

---

## Step 10: Share Your Repository

### Update Profile README

Add to your GitHub profile README:

```markdown
## 🤖 Featured Project: Canvas AI Auto-Grader

Autonomous AI-powered grading system that grades 35+ student submissions with 85% success rate using Claude Sonnet 4.5.

[View Repository →](https://github.com/YOUR_USERNAME/canvas-ai-auto-grader)
```

### Share on Social Media

**Twitter/X Template:**
```
🤖 Just built an AI-powered auto-grading system for Canvas LMS!

✅ 85% success rate
✅ Claude Sonnet 4.5 via @github Copilot
✅ 30-60s per submission
✅ 71% time saved vs manual grading

Check it out: [LINK]

#AI #Education #Python #GithubCopilot #Claude
```

**LinkedIn Template:**
```
🎓 Transforming Education with AI

I'm excited to share my latest project: Canvas AI Auto-Grader - an autonomous system that uses Claude Sonnet 4.5 to provide detailed, constructive feedback on student coding assignments.

Key Results from Production Testing:
• 85% success rate on 41 real submissions
• 100% automatic resolution of file lock errors
• 71% time savings vs manual grading
• Professional, encouraging feedback in 30-60 seconds

This project demonstrates the potential of AI to augment (not replace) educators, freeing up time for higher-value teaching activities.

Tech Stack: Python 3.11, GitHub Copilot SDK, Canvas LMS API, asyncio

#ArtificialIntelligence #Education #EdTech #Python #Automation
```

---

## Maintenance

### Regular Updates

```bash
# Keep dependencies updated
pip list --outdated

# Update requirements.txt
pip freeze > requirements.txt

# Commit and push
git add requirements.txt
git commit -m "chore: Update dependencies"
git push
```

### Monitor Issues

- Respond to issues within 48 hours
- Label issues (bug, enhancement, question, etc.)
- Close resolved issues with explanation

---

## Security Best Practices

### Never Commit These Files:
- ❌ config.json (contains API tokens)
- ❌ queue.json (contains student data)
- ❌ assignments/ folder (student work)
- ❌ .env files
- ❌ API keys or passwords

### Use GitHub Secrets for CI/CD

If you add GitHub Actions:
1. Settings → Secrets and variables → Actions
2. Add secrets: `CANVAS_API_TOKEN`, etc.
3. Reference in workflows with `${{ secrets.CANVAS_API_TOKEN }}`

---

## 🎉 You're Done!

Your private repository is now set up with:
- ✅ Professional README with screenshots
- ✅ Proper .gitignore for sensitive data
- ✅ Contributing guidelines
- ✅ Release tags and version history
- ✅ Security best practices
- ✅ Repository settings optimized

**Next Steps:**
1. Capture screenshots (see `docs/SCREENSHOT_GUIDE.md`)
2. Add collaborators if needed (Settings → Collaborators)
3. Star your own repo (why not? 😄)
4. Share with the education/AI community!

---

## Need Help?

If you encounter any issues during setup, feel free to:
- Check GitHub's documentation: https://docs.github.com/
- Ask in GitHub Discussions (after enabling)
- Reach out for assistance

Happy grading! 🚀
