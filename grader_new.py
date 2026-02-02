"""
New Grader Module

Grades submissions using GitHub Copilot SDK with cloned repositories.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel

# Import new modules
from assignments import save_grading_result
from repo_cloner import clone_repo, format_repo_for_grading, has_gh_cli
from canvas import CanvasClient

# Paths
PROMPTS_DIR = Path(__file__).parent / "prompts"
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


def get_submission_content(
    submission_type: str,
    submission_url: str,
    repo_path: Path,
    files_path: Path
) -> str:
    """
    Get submission content based on type.
    
    For GitHub repos, reads from cloned folder.
    For other types, extracts content.
    """
    if submission_type == "github":
        if repo_path.exists() and any(repo_path.iterdir()):
            # Use cloned repository
            return format_repo_for_grading(repo_path)
        else:
            return f"ERROR: Repository not cloned. URL: {submission_url}"
    
    elif submission_type == "pdf":
        # Extract PDF text from files/ folder
        pdf_files = list(files_path.glob("*.pdf"))
        if pdf_files:
            return extract_pdf_content(pdf_files[0])
        return "ERROR: No PDF file found"
    
    elif submission_type == "text":
        # Text submission (would be in submission metadata)
        return submission_url  # URL contains the text for text submissions
    
    elif submission_type == "url":
        return f"Submitted URL: {submission_url}\n\n(URL content not automatically fetched)"
    
    else:
        return f"Unknown submission type: {submission_type}"


def extract_pdf_content(pdf_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return "ERROR: PyPDF2 not installed"
    
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(f"--- Page {i+1} ---\n{text}")
        
        if not text_parts:
            return "PDF appears to be empty or contains only images"
        
        return "\n\n".join(text_parts)
    
    except Exception as e:
        return f"ERROR: Could not extract PDF: {str(e)}"


def build_grading_prompt(
    assignment_title: str,
    max_points: float,
    submission_type: str,
    student_login: str,
    submission_content: str
) -> str:
    """Build complete grading prompt from templates."""
    system_prompt = load_prompt("system")
    grading_prompt = load_prompt("grading")
    feedback_guide = load_prompt("feedback")
    rubric = load_rubric()
    
    # Fill template variables
    filled_prompt = grading_prompt.format(
        rubric=rubric,
        submission_type=submission_type,
        student_id=student_login,
        submission_content=submission_content,
        assignment_name=assignment_title,
        max_points=max_points
    )
    
    return f"{system_prompt}\n\n---\n\n{feedback_guide}\n\n---\n\n{filled_prompt}"


# Pydantic model for the grading tool
class SaveGradingParams(BaseModel):
    """Parameters for the save_grading tool that the AI uses."""
    score: float
    feedback: str


async def grade_with_copilot(
    assignment_id: str,
    assignment_title: str,
    max_points: float,
    student_login: str,
    submission_type: str,
    submission_url: str,
    repo_path: Path,
    files_path: Path
) -> Dict[str, Any]:
    """
    Grade a submission using GitHub Copilot SDK.
    
    Returns dict with:
    - success: bool
    - score: float (if success)
    - feedback: str (if success)
    - error: str (if failure)
    """
    try:
        from copilot import CopilotClient, define_tool
    except ImportError:
        return {
            "success": False,
            "error": "GitHub Copilot SDK not installed. Run: pip install github-copilot-sdk"
        }
    
    # Get submission content
    submission_content = get_submission_content(
        submission_type,
        submission_url,
        repo_path,
        files_path
    )
    
    # Build prompt
    prompt = build_grading_prompt(
        assignment_title,
        max_points,
        submission_type,
        student_login,
        submission_content
    )
    
    # Storage for AI's grading result
    grading_result = {"score": None, "feedback": None}
    
    # Define tool that AI will use to save grading
    @define_tool(
        description=f"""Save the grading result for this submission.

Call this tool with:
- score: A number between 0 and {max_points} representing the student's grade
- feedback: Markdown-formatted feedback following the template structure

The score must be between 0 and {max_points}.
The feedback should include:
- Strengths section (positive observations)
- Rubric breakdown (score per criterion)  
- Suggestions for improvement
- Summary with encouragement
"""
    )
    def save_grading(params: SaveGradingParams):
        """Save the grading result (score and feedback)."""
        grading_result["score"] = params.score
        grading_result["feedback"] = params.feedback
        return f"Grading saved successfully. Score: {params.score}/{max_points}"
    
    # Create Copilot client
    client = CopilotClient({
        "log_level": "error",
        "cli_path": os.environ.get("COPILOT_CLI_PATH")
    })
    
    try:
        await client.start()
        
        # Check authentication
        auth_status = await client.get_auth_status()
        if not auth_status.isAuthenticated:
            return {
                "success": False,
                "error": "Not authenticated with Copilot. Please authenticate."
            }
        
        # Create session with grading tool
        session = await client.create_session({
            "model": "claude-sonnet-4.5",
            "tools": [save_grading]
        })
        
        # Send grading prompt and wait for response
        done = asyncio.Event()
        error_message = None
        
        def on_event(event):
            nonlocal error_message
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            
            if event_type == "session.idle":
                done.set()
            elif event_type == "error":
                error_message = getattr(event.data, 'message', str(event.data))
                done.set()
        
        session.on(on_event)
        
        await session.send({
            "prompt": prompt
        })
        
        try:
            await asyncio.wait_for(done.wait(), timeout=120.0)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Grading timed out after 2 minutes"
            }
        
        if error_message:
            return {
                "success": False,
                "error": f"Copilot error: {error_message}"
            }
        
        # Check if AI provided grading
        if grading_result["score"] is None or grading_result["feedback"] is None:
            return {
                "success": False,
                "error": "AI did not provide complete grading (missing score or feedback)"
            }
        
        return {
            "success": True,
            "score": grading_result["score"],
            "feedback": grading_result["feedback"]
        }
    
    finally:
        try:
            await session.destroy()
        except:
            pass
        try:
            await client.stop()
        except:
            pass


def grade_mock(
    assignment_title: str,
    max_points: float,
    submission_type: str
) -> Dict[str, Any]:
    """Mock grading for testing without Copilot."""
    feedback = f"""# Grading Report

**Assignment:** {assignment_title}
**Score:** {max_points} / {max_points}

---

## 🌟 Strengths

Great submission! This is mock feedback for testing.

---

## 📊 Rubric Breakdown

### Submission: {max_points} / {max_points} points
- Submission received and processed successfully

---

## 🎯 Summary

Excellent work! (This is mock mode - enable AI grading with --no-mock)
"""
    
    return {
        "success": True,
        "score": max_points,
        "feedback": feedback
    }
