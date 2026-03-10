"""
Canvas API Client

Thin wrapper for Canvas LMS API to fetch submissions.
"""

import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from config import load_config


class CanvasClient:
    """Canvas LMS API client for fetching submissions."""

    def __init__(self):
        config = load_config()
        self.base_url = config.canvas.base_url
        self.api_token = config.canvas.api_token
        self.course_id = config.canvas.course_id
        
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
    
    def get_all_assignments(self, filter_keywords=None) -> List[Dict[str, Any]]:
        """
        Get all assignments for the course.

        Args:
            filter_keywords: A string or list of strings. If provided, only return
                           assignments matching ANY of the keywords in their name.

        Returns:
            List of assignment dicts with keys: id, name, points_possible, due_at, etc.
        """
        endpoint = f"/courses/{self.course_id}/assignments"
        assignments = self._get_paginated(endpoint)

        if filter_keywords:
            # Normalize to list
            if isinstance(filter_keywords, str):
                filter_keywords = [filter_keywords]
            keywords_lower = [k.lower() for k in filter_keywords if k]
            if keywords_lower:
                assignments = [
                    a for a in assignments
                    if any(kw in a.get("name", "").lower() for kw in keywords_lower)
                ]

        return assignments
    
    def get_assignment(self, assignment_id: str) -> Dict[str, Any]:
        """Get specific assignment details."""
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}"
        return self._get(endpoint)

    def get_assignment_with_rubric(self, assignment_id: str) -> Dict[str, Any]:
        """Get assignment details including rubric criteria if one is attached."""
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}"
        params = {"include[]": ["rubric_assessment"]}
        return self._get(endpoint, params)
    
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

    def _put(self, endpoint: str, data: Dict[str, Any]) -> Any:
        """Make PUT request to Canvas API."""
        url = f"{self.base_url}/api/v1{endpoint}"
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def post_grade(
        self,
        assignment_id: str,
        user_id: str,
        score: float,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Post a grade and optional comment to Canvas for a submission.

        Args:
            assignment_id: Canvas assignment ID
            user_id: Canvas user ID
            score: Numeric score to post
            comment: Optional text comment for the student

        Returns:
            Canvas API response dict
        """
        endpoint = f"/courses/{self.course_id}/assignments/{assignment_id}/submissions/{user_id}"
        data = {
            "submission": {
                "posted_grade": score
            }
        }
        if comment:
            data["comment"] = {
                "text_comment": comment
            }
        return self._put(endpoint, data)


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


def format_rubric_as_markdown(rubric_data: List[Dict[str, Any]], points_possible: float) -> str:
    """
    Convert Canvas rubric criteria to a markdown rubric file.

    Canvas rubric format:
    [
        {
            "id": "...",
            "description": "Criterion name",
            "long_description": "Details",
            "points": 10.0,
            "ratings": [
                {"description": "Excellent", "long_description": "...", "points": 10.0},
                {"description": "Good", "long_description": "...", "points": 7.0},
                ...
            ]
        },
        ...
    ]
    """
    sections = [f"# Assignment Grading Rubric\n\n**Total Points:** {points_possible}\n"]

    for criterion in rubric_data:
        name = criterion.get("description", "Unnamed Criterion")
        points = criterion.get("points", 0)
        long_desc = criterion.get("long_description", "")

        sections.append(f"## {name} ({points} points)\n")

        if long_desc:
            sections.append(f"{long_desc}\n")

        ratings = criterion.get("ratings", [])
        if ratings:
            sections.append("| Level | Points | Description |")
            sections.append("|-------|--------|-------------|")

            # Sort ratings by points descending
            sorted_ratings = sorted(ratings, key=lambda r: r.get("points", 0), reverse=True)

            for rating in sorted_ratings:
                r_desc = rating.get("description", "")
                r_points = rating.get("points", 0)
                r_long = rating.get("long_description", "")
                display = f"{r_desc}. {r_long}" if r_long else r_desc
                sections.append(f"| **{r_desc}** | {r_points} | {display} |")

            sections.append("")

    sections.append("---\n")
    sections.append("*This rubric was automatically pulled from Canvas.*\n")

    return "\n".join(sections)
