"""
GitHub Repository Cloning

Uses GitHub CLI (gh) to clone repositories for AI grading.
"""

import subprocess
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, Any


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
    
    Returns dict with 'owner' and 'repo' keys, or None if invalid.
    """
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\.]+?)(?:\.git)?(?:/.*)?$",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2)
            }
    
    return None


def clone_repo(github_url: str, dest_path: Path, timeout: int = 60) -> Dict[str, Any]:
    """
    Clone a GitHub repository using gh CLI.
    
    Args:
        github_url: GitHub repository URL
        dest_path: Destination folder (will be created/overwritten)
        timeout: Timeout in seconds
    
    Returns:
        Dict with:
        - success: bool
        - path: Path to cloned repo (if success)
        - error: Error message (if failure)
        - owner: Repository owner
        - repo: Repository name
    """
    if not has_gh_cli():
        return {
            "success": False,
            "error": "GitHub CLI (gh) is not installed. Install from https://cli.github.com/",
            "path": None,
            "owner": None,
            "repo": None
        }
    
    parsed = parse_github_url(github_url)
    if not parsed:
        return {
            "success": False,
            "error": f"Invalid GitHub URL: {github_url}",
            "path": None,
            "owner": None,
            "repo": None
        }
    
    owner = parsed["owner"]
    repo = parsed["repo"]
    
    # Remove existing clone if it exists
    if dest_path.exists():
        try:
            shutil.rmtree(dest_path)
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not remove existing clone: {e}",
                "path": None,
                "owner": owner,
                "repo": repo
            }
    
    # Ensure parent directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Clone using gh CLI
    try:
        result = subprocess.run(
            ["gh", "repo", "clone", f"{owner}/{repo}", str(dest_path)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "path": dest_path,
                "error": None,
                "owner": owner,
                "repo": repo
            }
        else:
            # Parse error message
            error = result.stderr.strip()
            
            # Common errors
            if "could not be cloned" in error or "not found" in error.lower():
                error = f"Repository {owner}/{repo} not found or not accessible"
            elif "authentication" in error.lower():
                error = "Authentication required. Run: gh auth login"
            elif "private" in error.lower() or "permission" in error.lower():
                error = f"Repository {owner}/{repo} is private or you don't have access"
            
            return {
                "success": False,
                "error": error,
                "path": None,
                "owner": owner,
                "repo": repo
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Clone timed out after {timeout} seconds",
            "path": None,
            "owner": owner,
            "repo": repo
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Clone failed: {str(e)}",
            "path": None,
            "owner": owner,
            "repo": repo
        }


def get_repo_stats(repo_path: Path) -> Dict[str, Any]:
    """
    Get basic statistics about a cloned repository.
    
    Returns dict with:
    - file_count: Number of files
    - total_size: Total size in bytes
    - file_types: Dict of extension -> count
    """
    if not repo_path.exists():
        return {"file_count": 0, "total_size": 0, "file_types": {}}
    
    file_count = 0
    total_size = 0
    file_types = {}
    
    for file_path in repo_path.rglob("*"):
        if file_path.is_file():
            # Skip .git folder
            if ".git" in file_path.parts:
                continue
            
            file_count += 1
            total_size += file_path.stat().st_size
            
            # Track file extension
            ext = file_path.suffix.lower()
            if ext:
                file_types[ext] = file_types.get(ext, 0) + 1
            else:
                file_types["[no extension]"] = file_types.get("[no extension]", 0) + 1
    
    return {
        "file_count": file_count,
        "total_size": total_size,
        "file_types": file_types
    }


def format_repo_for_grading(repo_path: Path, max_file_size: int = 50000) -> str:
    """
    Format cloned repository contents for AI grading.
    
    Creates a comprehensive text representation including:
    - File structure
    - README content
    - Key source files
    
    Args:
        repo_path: Path to cloned repository
        max_file_size: Max size in bytes to include full file content
    
    Returns:
        Formatted string for grading prompt
    """
    if not repo_path.exists():
        return "ERROR: Repository not found"
    
    sections = []
    
    # Header
    sections.append(f"# Repository: {repo_path.name}\n")
    
    # Stats
    stats = get_repo_stats(repo_path)
    sections.append(f"**Files:** {stats['file_count']}")
    sections.append(f"**Total Size:** {stats['total_size']:,} bytes\n")
    
    # File structure
    sections.append("## File Structure\n```")
    sections.append(_build_tree(repo_path))
    sections.append("```\n")
    
    # README
    readme_paths = ["README.md", "README.MD", "readme.md", "README.txt", "README"]
    for readme_name in readme_paths:
        readme_file = repo_path / readme_name
        if readme_file.exists():
            sections.append("## README\n")
            try:
                content = readme_file.read_text(encoding="utf-8", errors="ignore")
                sections.append(content[:5000])  # Truncate if very long
                if len(content) > 5000:
                    sections.append("\n... (truncated)")
            except Exception:
                sections.append("(Could not read README)")
            sections.append("\n")
            break
    
    # Key source files
    sections.append("## Source Files\n")
    source_exts = {".py", ".js", ".java", ".cpp", ".c", ".ts", ".go", ".rs", ".rb"}
    
    source_files = []
    for file_path in repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in source_exts:
            if ".git" not in file_path.parts:
                source_files.append(file_path)
    
    # Sort by file size (show smaller files first)
    source_files.sort(key=lambda p: p.stat().st_size)
    
    for source_file in source_files[:10]:  # Limit to 10 files
        rel_path = source_file.relative_to(repo_path)
        size = source_file.stat().st_size
        
        sections.append(f"### {rel_path} ({size} bytes)")
        
        if size <= max_file_size:
            try:
                content = source_file.read_text(encoding="utf-8", errors="ignore")
                sections.append(f"```{source_file.suffix[1:]}\n{content}\n```\n")
            except Exception:
                sections.append("(Could not read file)\n")
        else:
            sections.append("(File too large, skipped)\n")
    
    if len(source_files) > 10:
        sections.append(f"... and {len(source_files) - 10} more source files\n")
    
    return "\n".join(sections)


def _build_tree(path: Path, prefix: str = "", max_depth: int = 4, current_depth: int = 0) -> str:
    """Build ASCII tree representation of directory."""
    if current_depth >= max_depth:
        return prefix + "... (truncated)"
    
    lines = []
    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        
        for i, entry in enumerate(entries):
            # Skip .git folder
            if entry.name == ".git":
                continue
            
            is_last = i == len(entries) - 1
            current_prefix = "└── " if is_last else "├── "
            
            if entry.is_dir():
                lines.append(f"{prefix}{current_prefix}{entry.name}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                lines.append(_build_tree(entry, next_prefix, max_depth, current_depth + 1))
            else:
                size = entry.stat().st_size
                lines.append(f"{prefix}{current_prefix}{entry.name} ({size} bytes)")
    
    except PermissionError:
        lines.append(f"{prefix}(Permission denied)")
    
    return "\n".join(lines)
