"""
Grader Module

Handles single submission grading via GitHub Copilot SDK.
This is a thin wrapper - the intelligence lives in prompts.

The Copilot SDK requires the Copilot CLI binary which is included in @github/copilot npm package.
You need either:
1. npm install -g @github/copilot (and run 'copilot auth login')
2. Or set COPILOT_CLI_PATH to point to the copilot CLI binary
3. Or use a GitHub token with Copilot access via GITHUB_TOKEN env var

For VS Code users: The easiest path is using the Copilot extension's built-in authentication.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import local modules
from state import load_status, mark_graded
from github import fetch_repo_structure, format_for_grading
from canvas import CanvasClient

# Paths
PROMPTS_DIR = Path(__file__).parent / "prompts"
SUBMISSIONS_DIR = Path(__file__).parent / "submissions"
RUBRIC_FILE = Path(__file__).parent / "rubric.md"


def load_prompt(name: str) -> str:
    """Load a prompt file from the prompts directory."""
    prompt_file = PROMPTS_DIR / f"{name}.md"
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def load_rubric() -> str:
    """Load the grading rubric."""
    with open(RUBRIC_FILE, "r", encoding="utf-8") as f:
        return f.read()


def get_submission_content(submission: Dict[str, Any]) -> str:
    """
    Fetch the content of a submission based on its type.
    
    Returns formatted string for the grading prompt.
    """
    sub_type = submission["type"]
    
    if sub_type == "github":
        # Fetch GitHub repo structure
        try:
            repo_data = fetch_repo_structure(submission["url"])
            return format_for_grading(repo_data)
        except Exception as e:
            return f"Error fetching GitHub repository: {str(e)}\nURL: {submission['url']}"
    
    elif sub_type == "pdf":
        # Download and extract PDF text
        try:
            return extract_pdf_content(submission)
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    elif sub_type == "text":
        # Direct text submission
        return submission.get("body", "No content provided")
    
    elif sub_type == "url":
        # Non-GitHub URL
        return f"Submitted URL: {submission['url']}\n\n(URL content not automatically fetched)"
    
    else:
        return f"Unknown submission type: {sub_type}"


def extract_pdf_content(submission: Dict[str, Any]) -> str:
    """Extract text content from a PDF submission."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return "PyPDF2 not installed. Cannot extract PDF content."
    
    # Download PDF if needed
    student_dir = SUBMISSIONS_DIR / submission["student"]
    student_dir.mkdir(parents=True, exist_ok=True)
    
    filename = submission.get("filename", "submission.pdf")
    pdf_path = student_dir / filename
    
    if not pdf_path.exists():
        # Download from Canvas
        client = CanvasClient()
        client.download_file(submission["url"], pdf_path)
    
    # Extract text
    reader = PdfReader(pdf_path)
    text_parts = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            text_parts.append(f"--- Page {i+1} ---\n{text}")
    
    if not text_parts:
        return "PDF appears to be empty or contains only images (text extraction failed)"
    
    return "\n\n".join(text_parts)


def save_grading_file(
    student: str,
    score: float,
    feedback_md: str,
    submission: Dict[str, Any]
) -> str:
    """
    Save the grading feedback to a markdown file.
    
    Returns the path to the saved file.
    """
    student_dir = SUBMISSIONS_DIR / student
    student_dir.mkdir(parents=True, exist_ok=True)
    
    grading_file = student_dir / "grading.md"
    
    # Add metadata header
    header = f"""---
submission_id: {submission['id']}
student: {student}
score: {score}
graded_at: {datetime.now().isoformat()}
submission_type: {submission['type']}
submission_url: {submission.get('url', 'N/A')}
---

"""
    
    with open(grading_file, "w", encoding="utf-8") as f:
        f.write(header + feedback_md)
    
    return str(grading_file)


def build_grading_prompt(submission: Dict[str, Any]) -> str:
    """
    Build the complete grading prompt by combining templates.
    """
    # Load prompt templates
    system_prompt = load_prompt("system")
    grading_prompt = load_prompt("grading")
    feedback_guide = load_prompt("feedback")
    rubric = load_rubric()
    
    # Get submission content
    submission_content = get_submission_content(submission)
    
    # Get assignment info
    status = load_status()
    assignment_name = status.get("assignment", "Assignment")
    max_points = status.get("maxPoints", 100)
    
    # Fill in template variables
    filled_prompt = grading_prompt.format(
        rubric=rubric,
        submission_type=submission["type"],
        student_id=submission["student"],
        submission_content=submission_content,
        assignment_name=assignment_name,
        max_points=max_points
    )
    
    # Combine all prompts
    full_prompt = f"""
{system_prompt}

---

{feedback_guide}

---

{filled_prompt}
"""
    
    return full_prompt


def grade_submission_mock(submission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock grading function for testing without Copilot SDK.
    
    In production, replace with actual Copilot SDK call.
    """
    # Build the prompt (this is what would go to Copilot)
    prompt = build_grading_prompt(submission)
    
    status = load_status()
    max_points = status.get("maxPoints", 1)
    
    # For simple 0/1 grading, give full points if submission exists
    score = float(max_points)
    
    feedback_md = f"""# Grading Report

**Student:** {submission['student']}
**Assignment:** {status.get('assignment', 'Assignment')}
**Score:** {score} / {max_points}

---

## 🌟 Strengths

Great job submitting your work! Your GitHub repository link was successfully submitted.

---

## 📊 Rubric Breakdown

### GitHub Repository Submission: {score} / {max_points} points
Valid GitHub repository link submitted.

---

## 💡 Suggestions for Improvement

Keep up the good work! Make sure to explore more Git features like branching and pull requests.

---

## 🎯 Summary

Well done on completing this assignment! You've demonstrated understanding of the basics of GitHub.
"""
    
    # Save grading file
    grading_file = save_grading_file(
        submission["student"],
        score,
        feedback_md,
        submission
    )
    
    return {
        "success": True,
        "score": score,
        "grading_file": grading_file
    }


async def grade_submission_copilot(submission: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade a submission using GitHub Copilot SDK with OAuth authentication.
    
    Prerequisites:
    1. Install: pip install github-copilot-sdk
    2. Install Copilot CLI: npm install -g @github/copilot-cli (or download binary)
    3. Authenticate: copilot auth login
    
    The SDK uses the logged-in Copilot user's OAuth credentials automatically.
    """
    try:
        from copilot import CopilotClient
        from copilot.tools import define_tool
        from pydantic import BaseModel, Field
    except ImportError as e:
        raise ImportError(
            "github-copilot-sdk not installed. Run: pip install github-copilot-sdk\n"
            f"Error: {e}"
        )
    
    # Get assignment info for validation
    status = load_status()
    max_points = status.get("maxPoints", 100)
    
    # Mutable container to capture grading result from tool
    grading_result = {"success": False, "score": None, "grading_file": None}
    
    # Define the save_grading tool with Pydantic
    class SaveGradingParams(BaseModel):
        score: float = Field(
            description=f"The total numeric score (must be between 0 and {max_points})"
        )
        feedback_md: str = Field(
            description="Complete feedback in markdown format following the template provided"
        )
    
    @define_tool(
        description=f"""Save the grading results for the current submission.
        
Call this tool exactly ONCE after you have:
1. Analyzed the submission content
2. Evaluated against the rubric criteria
3. Written encouraging, specific feedback

The score must be between 0 and {max_points}.
The feedback_md should follow the template structure with:
- Strengths section (positive observations)
- Rubric breakdown (score per criterion)
- Suggestions for improvement
- Summary with encouragement
"""
    )
    async def save_grading(params: SaveGradingParams) -> str:
        # Validate score range
        if params.score < 0 or params.score > max_points:
            return f"Error: Score must be between 0 and {max_points}. Got: {params.score}"
        
        grading_file = save_grading_file(
            submission["student"],
            params.score,
            params.feedback_md,
            submission
        )
        grading_result["success"] = True
        grading_result["score"] = params.score
        grading_result["grading_file"] = grading_file
        return f"Grading saved successfully. Score: {params.score}/{max_points}, File: {grading_file}"
    
    # Build the system prompt with all context
    system_prompt = build_grading_prompt(submission)
    
    # Create Copilot client (uses OAuth - user must be logged in)
    client = CopilotClient({
        "log_level": "error",  # Reduce noise
        "auto_start": True,    # Auto-start CLI server
    })
    
    try:
        # Start the client
        await client.start()
        
        # Check authentication status
        auth_status = await client.get_auth_status()
        if not auth_status.isAuthenticated:
            raise RuntimeError(
                "Not authenticated with Copilot. Please run: copilot auth login"
            )
        
        # Create session with our grading tool
        session = await client.create_session({
            "model": "gpt-4.1",  # Use a capable model
            "tools": [save_grading],
            "system_message": {
                "content": system_prompt,
                "mode": "replace"  # Replace default system message entirely
            },
            "streaming": False,  # We don't need streaming for grading
        })
        
        # Event to wait for completion
        done = asyncio.Event()
        error_message = None
        
        def on_event(event):
            nonlocal error_message
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            
            if event_type == "session.idle":
                # Session finished processing
                done.set()
            elif event_type == "error":
                # Capture any errors
                error_message = getattr(event.data, 'message', str(event.data))
                done.set()
        
        # Subscribe to events
        session.on(on_event)
        
        # Send the grading request
        await session.send({
            "prompt": (
                "Please grade this submission according to the rubric and instructions provided. "
                "Analyze the submission content carefully, then call the save_grading tool with "
                "the appropriate score and detailed, encouraging feedback. "
                "Remember to be constructive and specific in your feedback."
            )
        })
        
        # Wait for completion (with timeout)
        try:
            await asyncio.wait_for(done.wait(), timeout=120.0)  # 2 minute timeout
        except asyncio.TimeoutError:
            raise RuntimeError("Grading timed out after 2 minutes")
        
        if error_message:
            raise RuntimeError(f"Copilot error: {error_message}")
        
        # Clean up session
        await session.destroy()
        
    finally:
        # Always stop the client
        await client.stop()
    
    if not grading_result["success"]:
        raise RuntimeError("Grading did not complete - save_grading tool was not called")
    
    return grading_result


def grade_submission(submission: Dict[str, Any], use_mock: bool = True) -> Dict[str, Any]:
    """
    Grade a single submission.
    
    Args:
        submission: The submission dict from status.json
        use_mock: If True, use mock grading; if False, use Copilot SDK with OAuth
    
    Returns:
        Dict with keys: success, score, grading_file
    """
    if use_mock:
        return grade_submission_mock(submission)
    else:
        return asyncio.run(grade_submission_copilot(submission))


async def check_copilot_auth() -> Dict[str, Any]:
    """
    Check if Copilot SDK is available and user is authenticated.
    
    Returns dict with:
    - authenticated: bool
    - login: str (username if authenticated)
    - message: str (status message)
    - cli_available: bool
    """
    # First check if SDK is installed
    try:
        from copilot import CopilotClient
    except ImportError:
        return {
            "authenticated": False,
            "login": None,
            "cli_available": False,
            "message": "github-copilot-sdk not installed. Run: pip install github-copilot-sdk"
        }
    
    # Check if CLI binary is available
    cli_path = os.environ.get("COPILOT_CLI_PATH")
    
    # Try to find the CLI if not set in env
    import shutil
    import subprocess
    
    if cli_path and os.path.isfile(cli_path):
        cli_found = True
    else:
        # Check common locations
        possible_paths = [
            # npm global install (Windows)
            os.path.expanduser("~/AppData/Roaming/npm/copilot.cmd"),
            os.path.expanduser("~/AppData/Roaming/npm/copilot"),
            # npm global install (Unix)
            os.path.expanduser("~/.npm-global/bin/copilot"),
            "/usr/local/bin/copilot",
            # Local node_modules (if they cloned the SDK repo)
            "./node_modules/@github/copilot/index.js",
            "../nodejs/node_modules/@github/copilot/index.js",
        ]
        
        cli_found = False
        for path in possible_paths:
            if os.path.isfile(path):
                cli_path = path
                cli_found = True
                break
        
        # Also try which/where command
        if not cli_found:
            found = shutil.which("copilot")
            if found:
                cli_path = found
                cli_found = True
    
    if not cli_found:
        return {
            "authenticated": False,
            "login": None,
            "cli_available": False,
            "message": (
                "Copilot CLI not found. Install with:\n"
                "  npm install -g @github/copilot\n"
                "Or set COPILOT_CLI_PATH environment variable.\n\n"
                "Alternatively, you can use the mock grading mode (default)."
            )
        }
    
    # CLI found - try to start client and check auth
    try:
        client = CopilotClient({
            "log_level": "error",
            "cli_path": cli_path
        })
        
        await client.start()
        auth_status = await client.get_auth_status()
        
        if auth_status.isAuthenticated:
            return {
                "authenticated": True,
                "login": auth_status.login,
                "cli_available": True,
                "message": f"Authenticated as {auth_status.login}"
            }
        else:
            return {
                "authenticated": False,
                "login": None,
                "cli_available": True,
                "message": "CLI found but not authenticated. Run: copilot auth login"
            }
    except FileNotFoundError:
        return {
            "authenticated": False,
            "login": None,
            "cli_available": False,
            "message": (
                "Copilot CLI not found (path exists but not executable).\n"
                "Install with: npm install -g @github/copilot"
            )
        }
    except Exception as e:
        return {
            "authenticated": False,
            "login": None,
            "cli_available": False,
            "message": f"Error starting Copilot: {str(e)}"
        }
    finally:
        try:
            await client.stop()
        except:
            pass
