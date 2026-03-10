"""
Assignment Folder Structure Management

Creates and manages folder structure:
assignments/
└── {assignment_id}_{title}/
    ├── assignment.json
    └── submissions/
        └── {student_login}/
            ├── repo/         # Cloned GitHub repo
            ├── files/        # Downloaded files
            └── grading.md    # AI feedback
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import shutil

from config import load_config


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a folder name.
    
    Replaces spaces with underscores, removes special chars.
    """
    # Replace spaces and special chars
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s]+', '_', name)
    return name[:100]  # Limit length


def get_assignment_folder(assignment_id: str, assignment_title: str) -> Path:
    """
    Get the folder path for an assignment.
    
    Creates: assignments/{assignment_id}_{sanitized_title}/
    """
    config = load_config()
    base_path = Path(config.grading.clone_path)

    sanitized_title = sanitize_filename(assignment_title)
    folder_name = f"{assignment_id}_{sanitized_title}"

    return base_path / folder_name


def get_submission_folder(assignment_id: str, assignment_title: str, student_login: str) -> Path:
    """
    Get the folder path for a student's submission.
    
    Creates: assignments/{assignment_id}_{title}/submissions/{student_login}/
    """
    assignment_folder = get_assignment_folder(assignment_id, assignment_title)
    return assignment_folder / "submissions" / sanitize_filename(student_login)


def create_assignment_structure(assignment_id: str, assignment_title: str, assignment_data: Dict[str, Any]) -> Path:
    """
    Create folder structure for an assignment and save metadata.
    
    Returns the assignment folder path.
    """
    assignment_folder = get_assignment_folder(assignment_id, assignment_title)
    submissions_folder = assignment_folder / "submissions"
    
    # Create directories
    assignment_folder.mkdir(parents=True, exist_ok=True)
    submissions_folder.mkdir(exist_ok=True)
    
    # Save assignment metadata
    assignment_json = assignment_folder / "assignment.json"
    with open(assignment_json, "w", encoding="utf-8") as f:
        json.dump(assignment_data, f, indent=2)
    
    return assignment_folder


def create_submission_structure(assignment_id: str, assignment_title: str, student_login: str) -> Dict[str, Path]:
    """
    Create folder structure for a student's submission.
    
    Returns dict with paths:
    - base: submissions/{student}/
    - repo: submissions/{student}/repo/
    - files: submissions/{student}/files/
    - grading: submissions/{student}/grading.md
    """
    submission_folder = get_submission_folder(assignment_id, assignment_title, student_login)
    repo_folder = submission_folder / "repo"
    files_folder = submission_folder / "files"
    grading_file = submission_folder / "grading.md"
    
    # Create directories
    submission_folder.mkdir(parents=True, exist_ok=True)
    repo_folder.mkdir(exist_ok=True)
    files_folder.mkdir(exist_ok=True)
    
    return {
        "base": submission_folder,
        "repo": repo_folder,
        "files": files_folder,
        "grading": grading_file
    }


def list_all_assignments() -> List[Dict[str, Any]]:
    """
    List all assignment folders.
    
    Returns list of dicts with:
    - assignment_id: str
    - title: str
    - folder: Path
    - metadata: Dict (from assignment.json)
    """
    config = load_config()
    base_path = Path(config.grading.clone_path)

    if not base_path.exists():
        return []

    assignments = []
    for folder in base_path.iterdir():
        if not folder.is_dir():
            continue
        
        # Parse folder name: {id}_{title}
        parts = folder.name.split("_", 1)
        if len(parts) != 2:
            continue
        
        assignment_id, title = parts
        
        # Load metadata if exists
        metadata_file = folder / "assignment.json"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        
        assignments.append({
            "assignment_id": assignment_id,
            "title": title.replace("_", " "),
            "folder": folder,
            "metadata": metadata
        })
    
    return assignments


def cleanup_old_repos(days: int = 7) -> int:
    """
    Delete cloned repos older than N days to save disk space.
    
    Only deletes repo/ folders, keeps grading.md and files/.
    Returns number of repos deleted.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    config = load_config()
    base_path = Path(config.grading.clone_path)

    if not base_path.exists():
        return 0
    
    # Find all repo/ folders
    for repo_folder in base_path.rglob("repo"):
        if not repo_folder.is_dir():
            continue
        
        # Check modification time
        mtime = datetime.fromtimestamp(repo_folder.stat().st_mtime)
        if mtime < cutoff_date:
            try:
                shutil.rmtree(repo_folder)
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {repo_folder}: {e}")
    
    return deleted_count


def get_submission_paths(assignment_id: str, assignment_title: str, student_login: str) -> Optional[Dict[str, Path]]:
    """
    Get paths for an existing submission (without creating).
    
    Returns None if submission folder doesn't exist, otherwise dict with paths.
    """
    submission_folder = get_submission_folder(assignment_id, assignment_title, student_login)
    
    if not submission_folder.exists():
        return None
    
    return {
        "base": submission_folder,
        "repo": submission_folder / "repo",
        "files": submission_folder / "files",
        "grading": submission_folder / "grading.md"
    }


def save_grading_result(
    assignment_id: str,
    assignment_title: str,
    student_login: str,
    submission_data: Dict[str, Any],
    score: float,
    feedback: str
) -> Path:
    """
    Save grading result to grading.md with YAML frontmatter.
    
    Returns path to created grading.md file.
    """
    paths = create_submission_structure(assignment_id, assignment_title, student_login)
    grading_file = paths["grading"]
    
    # Create YAML frontmatter
    frontmatter = [
        "---",
        f"submission_id: {submission_data.get('id', 'unknown')}",
        f"student: {student_login}",
        f"assignment_id: {assignment_id}",
        f"assignment_title: {assignment_title}",
        f"score: {score}",
        f"graded_at: {datetime.now().isoformat()}",
        f"submission_type: {submission_data.get('type', 'unknown')}",
        f"submission_url: {submission_data.get('url', '')}",
        "---",
        ""
    ]
    
    content = "\n".join(frontmatter) + feedback
    
    grading_file.write_text(content, encoding="utf-8")
    
    return grading_file
