"""
GitHub Repository Structure Fetcher

Fetches repo structure and key files via GitHub CLI (gh) or API fallback.
"""

import requests
import base64
import subprocess
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config() -> Dict[str, Any]:
    """Load GitHub configuration."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def has_gh_cli() -> bool:
    """Check if GitHub CLI (gh) is installed."""
    return shutil.which("gh") is not None


def parse_github_url(url: str) -> Optional[Dict[str, str]]:
    """
    Parse a GitHub URL to extract owner and repo.
    
    Handles formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/tree/branch
    - github.com/owner/repo
    """
    patterns = [
        r"github\.com/([^/]+)/([^/\.]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2).replace(".git", "")
            }
    
    return None


class GitHubClient:
    """GitHub API client for fetching repo structure."""
    
    def __init__(self):
        config = load_config()
        self.api_token = config.get("github", {}).get("api_token", "")
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.api_token:
            self.headers["Authorization"] = f"token {self.api_token}"
    
    def _get(self, endpoint: str) -> Any:
        """Make GET request to GitHub API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get basic repository information."""
        return self._get(f"/repos/{owner}/{repo}")
    
    def get_contents(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """Get contents of a directory in the repo."""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        result = self._get(endpoint)
        
        # API returns a list for directories, single object for files
        if isinstance(result, dict):
            return [result]
        return result
    
    def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Get the content of a specific file."""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        result = self._get(endpoint)
        
        if result.get("encoding") == "base64":
            content = base64.b64decode(result["content"]).decode("utf-8")
            return content
        
        return result.get("content", "")
    
    def get_tree_recursive(
        self, 
        owner: str, 
        repo: str, 
        path: str = "", 
        max_depth: int = 3,
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        Recursively build a tree structure of the repository.
        
        Returns a nested dict representing the file structure.
        """
        if current_depth >= max_depth:
            return {"_truncated": True}
        
        tree = {}
        
        try:
            contents = self.get_contents(owner, repo, path)
        except requests.HTTPError:
            return {"_error": "Could not fetch contents"}
        
        for item in contents:
            name = item["name"]
            
            if item["type"] == "dir":
                # Recursively get directory contents
                subpath = f"{path}/{name}" if path else name
                tree[name + "/"] = self.get_tree_recursive(
                    owner, repo, subpath, max_depth, current_depth + 1
                )
            else:
                # File - just record name and size
                tree[name] = {
                    "size": item.get("size", 0),
                    "type": "file"
                }
        
        return tree


def format_tree(tree: Dict[str, Any], indent: int = 0) -> str:
    """Format a tree dict as a string representation."""
    lines = []
    prefix = "  " * indent
    
    for name, value in sorted(tree.items()):
        if name.startswith("_"):
            continue
        
        if isinstance(value, dict):
            if value.get("type") == "file":
                size = value.get("size", 0)
                lines.append(f"{prefix}{name} ({size} bytes)")
            else:
                lines.append(f"{prefix}{name}")
                lines.append(format_tree(value, indent + 1))
        else:
            lines.append(f"{prefix}{name}")
    
    return "\n".join(lines)


def fetch_repo_structure(github_url: str) -> Dict[str, Any]:
    """
    Fetch the structure of a GitHub repository.
    
    Returns:
        Dict with keys:
        - owner: repo owner
        - repo: repo name
        - description: repo description
        - tree: nested dict of file structure
        - tree_string: formatted string representation
        - readme: README content if found
        - key_files: dict of important file contents
    """
    parsed = parse_github_url(github_url)
    if not parsed:
        raise ValueError(f"Could not parse GitHub URL: {github_url}")
    
    owner = parsed["owner"]
    repo = parsed["repo"]
    
    client = GitHubClient()
    
    # Get repo info
    try:
        repo_info = client.get_repo_info(owner, repo)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Repository not found: {owner}/{repo}")
        raise
    
    # Get file tree
    tree = client.get_tree_recursive(owner, repo)
    tree_string = format_tree(tree)
    
    # Try to get README
    readme = ""
    readme_names = ["README.md", "README.MD", "readme.md", "README.txt", "README"]
    for readme_name in readme_names:
        try:
            readme = client.get_file_content(owner, repo, readme_name)
            break
        except requests.HTTPError:
            continue
    
    # Try to get key files (common in programming assignments)
    key_files = {}
    important_files = [
        "main.py", "app.py", "index.py", "solution.py",
        "main.js", "index.js", "app.js",
        "Main.java", "App.java",
        "main.c", "main.cpp",
        "requirements.txt", "package.json", "Cargo.toml",
        "Makefile", "setup.py"
    ]
    
    for filename in important_files:
        try:
            content = client.get_file_content(owner, repo, filename)
            key_files[filename] = content
        except requests.HTTPError:
            continue
    
    # Also check src/ directory for main files
    try:
        src_contents = client.get_contents(owner, repo, "src")
        for item in src_contents:
            if item["type"] == "file" and item["name"] in important_files:
                try:
                    content = client.get_file_content(owner, repo, f"src/{item['name']}")
                    key_files[f"src/{item['name']}"] = content
                except requests.HTTPError:
                    continue
    except requests.HTTPError:
        pass
    
    return {
        "owner": owner,
        "repo": repo,
        "description": repo_info.get("description", ""),
        "language": repo_info.get("language", "Unknown"),
        "tree": tree,
        "tree_string": tree_string,
        "readme": readme,
        "key_files": key_files
    }


def format_for_grading(repo_data: Dict[str, Any]) -> str:
    """
    Format repo data as a string for the grading prompt.
    """
    sections = []
    
    # Header
    sections.append(f"# Repository: {repo_data['owner']}/{repo_data['repo']}")
    sections.append(f"**Language:** {repo_data['language']}")
    if repo_data['description']:
        sections.append(f"**Description:** {repo_data['description']}")
    
    # File structure
    sections.append("\n## File Structure\n```")
    sections.append(repo_data['tree_string'])
    sections.append("```")
    
    # README
    if repo_data['readme']:
        sections.append("\n## README.md\n")
        sections.append(repo_data['readme'][:3000])  # Truncate if very long
        if len(repo_data['readme']) > 3000:
            sections.append("\n... (truncated)")
    
    # Key files
    if repo_data['key_files']:
        sections.append("\n## Key Files\n")
        for filename, content in repo_data['key_files'].items():
            sections.append(f"### {filename}\n```")
            sections.append(content[:2000])  # Truncate if very long
            if len(content) > 2000:
                sections.append("\n... (truncated)")
            sections.append("```\n")
    
    return "\n".join(sections)
