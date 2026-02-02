"""
State management for status.json

Handles all CRUD operations for submission tracking.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

STATUS_FILE = Path(__file__).parent / "status.json"


def load_status() -> Dict[str, Any]:
    """Load status.json, creating default if not exists."""
    if not STATUS_FILE.exists():
        default = {
            "assignment": "",
            "maxPoints": 100,
            "submissions": []
        }
        save_status(default)
        return default
    
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_status(status: Dict[str, Any]) -> None:
    """Save status to status.json."""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Get a single submission by ID."""
    status = load_status()
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            return sub
    return None


def get_next_pending() -> Optional[Dict[str, Any]]:
    """Get the oldest pending submission (by stagedAt timestamp)."""
    status = load_status()
    pending = [s for s in status["submissions"] if s["status"] == "pending"]
    
    if not pending:
        return None
    
    # Sort by stagedAt (oldest first)
    pending.sort(key=lambda x: x.get("stagedAt", ""))
    return pending[0]


def get_submissions_by_status(target_status: str) -> List[Dict[str, Any]]:
    """Get all submissions with a specific status."""
    status = load_status()
    return [s for s in status["submissions"] if s["status"] == target_status]


def add_submission(
    submission_id: str,
    student: str,
    submission_type: str,
    url: str
) -> Dict[str, Any]:
    """Add a new submission with pending status."""
    status = load_status()
    
    # Check if already exists
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            return sub  # Already tracked
    
    new_submission = {
        "id": submission_id,
        "student": student,
        "type": submission_type,
        "url": url,
        "status": "pending",
        "score": None,
        "gradingFile": None,
        "error": None,
        "stagedAt": datetime.now().isoformat(),
        "gradedAt": None
    }
    
    status["submissions"].append(new_submission)
    save_status(status)
    return new_submission


def mark_grading(submission_id: str) -> bool:
    """Mark submission as currently being graded."""
    status = load_status()
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            sub["status"] = "grading"
            save_status(status)
            return True
    return False


def mark_graded(
    submission_id: str,
    score: float,
    grading_file: str
) -> bool:
    """Mark submission as successfully graded."""
    status = load_status()
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            sub["status"] = "graded"
            sub["score"] = score
            sub["gradingFile"] = grading_file
            sub["error"] = None
            sub["gradedAt"] = datetime.now().isoformat()
            save_status(status)
            return True
    return False


def mark_failed(submission_id: str, error: str) -> bool:
    """Mark submission as failed with error message."""
    status = load_status()
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            sub["status"] = "failed"
            sub["error"] = error
            save_status(status)
            return True
    return False


def reset_to_pending(submission_id: str) -> bool:
    """Reset a failed submission back to pending (for retry)."""
    status = load_status()
    for sub in status["submissions"]:
        if sub["id"] == submission_id:
            sub["status"] = "pending"
            sub["error"] = None
            sub["stagedAt"] = datetime.now().isoformat()
            save_status(status)
            return True
    return False


def get_status_summary() -> Dict[str, int]:
    """Get count of submissions by status."""
    status = load_status()
    summary = {
        "pending": 0,
        "grading": 0,
        "graded": 0,
        "failed": 0,
        "total": len(status["submissions"])
    }
    for sub in status["submissions"]:
        if sub["status"] in summary:
            summary[sub["status"]] += 1
    return summary


def update_assignment_info(name: str, max_points: int) -> None:
    """Update assignment name and max points."""
    status = load_status()
    status["assignment"] = name
    status["maxPoints"] = max_points
    save_status(status)
