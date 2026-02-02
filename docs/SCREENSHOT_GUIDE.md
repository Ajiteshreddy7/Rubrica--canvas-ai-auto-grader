
# 📸 Screenshot Guide for README

This guide will help you capture all the images referenced in the README.md file.

## Required Screenshots

### 1. **demo.gif** - Main Demo Animation
**What to capture:**
- Run `.\run.ps1 --no-mock` 
- Record the terminal from start to finish showing:
  - Daemon startup
  - Syncing assignments
  - Processing 3-4 submissions
  - Showing completed status
  
**Tools:** 
- Windows: Use **ScreenToGif** (free) https://www.screentogif.com/
- Alternative: **LICEcap** https://www.cockos.com/licecap/

**Recommended size:** 800-900px wide

**Tips:**
- Keep recording under 30 seconds
- Show different colored outputs (green success, red error)
- Zoom terminal to 150% for readability

---

### 2. **daemon-running.png** - Daemon in Action
**What to capture:**
- Full terminal window showing:
  ```
  🤖 Canvas Auto-Grading Daemon
  Mode: AI
  
  ═══ Cycle 1 ═══
  📥 Polling for new submissions...
  ✓ Added 6 new submissions to queue
  
  ⚙ Processing: Jakob Olsen - Hands-on L2: Basics of GitHub
    → Cloning repository...
    ✓ Cloned successfully
    → Grading...
    ✓ Graded: 1.0/1.0
  ```

**Tool:** Windows Snipping Tool (Win + Shift + S)

**Size:** ~700px wide

**Tips:**
- Capture when processing is active
- Show the rich colored output
- Include multiple completed items

---

### 3. **ai-feedback-example.png** - AI Feedback File
**What to capture:**
- Open one of the grading.md files in VS Code:
  ```
  assignments/2772299_Hands-on_L2.../submissions/Jakob_Olsen/grading.md
  ```
- Show the YAML frontmatter and feedback sections

**Tool:** Snipping Tool or VS Code screenshot

**Size:** ~600px wide

**What should be visible:**
```markdown
---
student: Jakob Olsen
score: 1.0
---

# Grading Feedback

## 🌟 Strengths
- Excellent repository structure...

## 💡 Suggestions for Growth
- Consider adding inline comments...
```

---

### 4. **retry-logic.png** - Retry in Action
**What to capture:**
- Terminal showing the retry section:
  ```
  🔄 Retrying 8 failed submission(s)...
    Cleaned 3 locked folder(s)
  ✓ Moved 8 item(s) back to queue
  📋 Processing retries...
  
  ⚙ Processing: Jakob Olsen - Hands-on L2
    ✓ Cloned successfully
    ✓ Graded: 1.0/1.0
  ```

**Size:** ~700px wide

---

### 5. **status-dashboard.png** - Status Command Output
**What to capture:**
- Run `.\status.ps1 -Detailed`
- Capture the full output showing:
  - Progress bar
  - Summary stats (completed, pending, failed)
  - Recently completed list
  - Failed submissions grouped by error

**Size:** ~700px wide

**Tips:**
- Make sure progress bar is visible
- Show variety of statuses

---

### 6. **prompt-architecture.png** - Prompt Files
**What to capture:**
- VS Code Explorer showing the `prompts/` folder expanded:
  ```
  prompts/
  ├── system.md
  ├── grading.md
  ├── feedback.md
  └── rubric.md
  ```
- Have one of the files open showing the content

**Size:** ~600px wide

**Tool:** VS Code screenshot (Ctrl + K, V to open markdown preview side-by-side)

---

### 7. **architecture-diagram.png** - System Architecture
**What to create:**
- Use a diagramming tool:
  - **Excalidraw** (https://excalidraw.com/) - Free, simple
  - **Draw.io** (https://app.diagrams.net/) - Free, professional
  - **Mermaid Live** (https://mermaid.live/) - Generate from code

**Components to show:**
```
Canvas LMS → Daemon → Queue → Clone Repo → AI Grader → Save Results
     ↓                                          ↓
   Polling                                   Feedback
```

**Size:** ~800px wide

**Style:** Clean, modern, with icons if possible

---

### 8. **full-workflow.png** - Complete Cycle
**What to capture:**
- Extended terminal output showing complete cycle:
  1. Syncing assignments (top)
  2. Polling submissions (middle)
  3. Processing multiple students (middle)
  4. Status summary (bottom)

**Size:** ~900px wide (can be tall)

**Tips:**
- This should be the most comprehensive screenshot
- Show at least 3-5 completed gradings
- Include the status panel at bottom

---

### 9. **grading-output.png** - Grading File in Editor
**What to capture:**
- Open a grading.md file in VS Code with markdown preview
- Show both the raw markdown and the rendered preview side-by-side

**Size:** ~700px wide

**Tool:** VS Code split view (Ctrl + K, V)

---

### 10. **error-handling.png** - Error Messages
**What to capture:**
- Terminal showing different types of errors:
  ```
  ⚙ Processing: Michael Thompson - Hands-on L2
    → Cloning repository...
    ✗ Clone failed: GraphQL: Could not resolve to a Repository...
  
  ❌ 6 submission(s) require human review:
    • Michael Thompson: Invalid repo (attempts: 2)
    • Het Patel: Invalid GitHub URL (attempts: 2)
  ```

**Size:** ~700px wide

---

### 11. **folder-structure.png** - File Explorer
**What to capture:**
- Windows Explorer showing the `assignments/` folder structure:
  ```
  assignments/
  └── 2772299_Hands-on_L2_Basics_of_GitHub/
      ├── assignment.json
      └── submissions/
          ├── Jakob_Olsen/
          │   ├── repo/
          │   │   ├── README.md
          │   │   └── main.py
          │   └── grading.md
          ├── Sunaina_Agarwal/
          └── ...
  ```

**Size:** ~600px wide

**Tips:**
- Expand 2-3 levels deep
- Show the repo/ folder contents
- Make sure grading.md is visible

---

## Screenshot Settings

### For All Screenshots:
1. **Resolution:** Capture at your current screen resolution
2. **Format:** PNG (for static), GIF (for animations)
3. **Background:** Dark terminal theme for better visibility
4. **Terminal Font Size:** Increase to 14-16pt for readability
5. **Color Scheme:** Use default Rich colors (green, red, cyan, yellow)

### Terminal Preparation:
```powershell
# Set terminal to good size
# Adjust font size in Terminal Settings → Appearance → Font size: 14
# Use Windows Terminal for better colors
```

---

## Quick Capture Checklist

- [ ] demo.gif - Full workflow animation
- [ ] daemon-running.png - Active processing
- [ ] ai-feedback-example.png - Feedback file
- [ ] retry-logic.png - Retry messages
- [ ] status-dashboard.png - Status command
- [ ] prompt-architecture.png - Prompts folder
- [ ] architecture-diagram.png - System diagram
- [ ] full-workflow.png - Complete cycle
- [ ] grading-output.png - VS Code preview
- [ ] error-handling.png - Error messages
- [ ] folder-structure.png - File explorer

---

## After Capturing Screenshots

1. Save all images to `docs/images/` folder
2. Optimize images (compress without losing quality):
   - Use **TinyPNG** https://tinypng.com/
   - Or **Squoosh** https://squoosh.app/
3. Check README.md renders correctly with images
4. Push to GitHub and verify in browser

---

## Optional Enhancements

### Add Annotations
Use **Greenshot** or **ShareX** to add:
- Arrows pointing to important features
- Text boxes explaining key parts
- Highlights on critical sections

### Create Comparison Images
Show "Before vs After" side-by-side:
- Manual grading spreadsheet vs automated dashboard
- Hours of work vs minutes

---

## Need Help?

If you need specific examples of how to capture any of these, let me know which screenshot and I can provide more detailed instructions!
