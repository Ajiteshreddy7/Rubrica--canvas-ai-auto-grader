"""
Canvas API Client

Thin wrapper for Canvas LMS API to fetch submissions.
"""

import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config() -> Dict[str, Any]:
    """Load Canvas configuration."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class CanvasClient:
    """Canvas LMS API client for fetching submissions."""
    
    def __init__(self):
        config = load_config()
        self.base_url = config["canvas"]["base_url"].rstrip("/")
        self.api_token = config["canvas"]["api_token"]
        self.course_id = config["canvas"]["course_id"]
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make GET request to Canvas API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def _get_paginated(self, endpoint: str, params: Optional[Dict] = None) -> List[Any]:
        """Handle paginated Canvas API responses."""
        results = []
        url = f"{self.base_url}/api/v1{endpoint}"
        params = params or {}
        params["per_page"] = 100
        
        while url:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            results.extend(response.json())
            
            # Check for next page
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<> ")
                    params = {}  # Params are in the URL for subsequent requests
                    break
        
        return results
    
    def get_all_assignments(self, filter_keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all assignments for the course.
        
        Args:
            filter_keyword: If provided, only return assignments with this keyword in the name
        
        Returns:
            List of assignment dicts with keys: id, name, points_possible, due_at, etc.
        """
        endpoint = f"/courses/{self.course_id}/assignments"
        assignments = self._get_paginated(endpoint)
        
        if filter_keyword:
            filter_lower = filter_keyword.lower()
            assignments = [a for a in assignments if filter_lower in a.get("name", "").lower()]
        
        return assignments
    
    def get_assignment(self, assignment_id: str) -> Dict[str, Any]:
        """Get specific assignment details."""
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}"
        return self._get(endpoint)
    
    def get_submissions(self, assignment_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for a specific assignment."""
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}/submissions"
        params = {"include[]": ["user"]}
        return self._get_paginated(endpoint, params)
    
    def get_submission(self, assignment_id: str, user_id: str) -> Dict[str, Any]:
        """Get a single submission by assignment and user ID."""
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}/submissions/{user_id}"
        params = {"include[]": ["user"]}
        return self._get(endpoint, params)
    
    def download_file(self, file_url: str, save_path: Path) -> Path:
        """Download a file attachment from Canvas."""
        # Canvas file URLs require authentication
        response = requests.get(file_url, headers=self.headers, stream=True)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return save_path


def parse_submission(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a raw Canvas submission into our format.
    
    Returns None if submission is empty/not submitted.
    """
    # Skip if not actually submitted
    if raw.get("workflow_state") == "unsubmitted":
        return None
    
    if not raw.get("submitted_at"):
        return None
    
    submission_type = raw.get("submission_type")
    
    # Get student identifier
    user = raw.get("user", {})
    student = user.get("login_id") or user.get("name") or str(raw.get("user_id", "unknown"))
    
    # Parse based on submission type
    if submission_type == "online_url":
        # URL submission (likely GitHub)
        url = raw.get("url", "")
        return {
            "id": str(raw["id"]),
            "student": student,
            "type": "github" if "github.com" in url.lower() else "url",
            "url": url
        }
    
    elif submission_type == "online_upload":
        # File upload (likely PDF)
        attachments = raw.get("attachments", [])
        if attachments:
            attachment = attachments[0]  # Take first attachment
            return {
                "id": str(raw["id"]),
                "student": student,
                "type": "pdf" if attachment.get("content-type") == "application/pdf" else "file",
                "url": attachment.get("url", ""),
                "filename": attachment.get("filename", "submission")
            }
    
    elif submission_type == "online_text_entry":
        # Text entry submission
        return {
            "id": str(raw["id"]),
            "student": student,
            "type": "text",
            "url": "",
            "body": raw.get("body", "")
        }
    
    return None


def fetch_new_submissions(existing_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch submissions from Canvas that aren't already tracked.
    
    Args:
        existing_ids: List of submission IDs already in status.json
    
    Returns:
        List of new submissions to stage
    """
    client = CanvasClient()
    raw_submissions = client.get_submissions()
    
    new_submissions = []
    for raw in raw_submissions:
        parsed = parse_submission(raw)
        if parsed and parsed["id"] not in existing_ids:
            new_submissions.append(parsed)
    
    return new_submissions
