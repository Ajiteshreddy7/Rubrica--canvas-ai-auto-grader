"""
Publish Analytics Dashboard to GitHub Pages

Uses git plumbing commands to update a gh-pages branch without touching the
working tree.  Safe to call while a daemon is running -- no branch switching,
no stashing.
"""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from logger import log

# GitHub Pages metadata
OWNER = "Ajiteshreddy7"
REPO = "Rubrica--canvas-ai-auto-grader"
PAGES_URL = f"https://{OWNER.lower()}.github.io/{REPO}/"


def _run_git(*args: str) -> str:
    """Run a git command and return stripped stdout.  Raises on failure."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_gh(*args: str) -> str:
    """Run a GitHub CLI command and return stripped stdout."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def publish_dashboard(verbose: bool = True) -> bool:
    """
    Generate the analytics HTML report and publish it to GitHub Pages
    via the gh-pages branch, using git plumbing (no working-tree changes).

    Returns True on success, False if there is no grading data yet.
    """
    from analytics import generate_full_report
    from report_generator import generate_html_report

    # 1. Generate report data
    report = generate_full_report()
    if report.get("record_count", 0) == 0:
        if verbose:
            print("No grading data to publish.")
        return False

    # 2. Render HTML to a temp file
    tmp = tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    )
    try:
        tmp_path = tmp.name
        tmp.close()
        generate_html_report(report, tmp_path)

        # 3. Create blob from HTML file
        blob_sha = _run_git("hash-object", "-w", tmp_path)

        # 4. Create tree with a single entry: index.html
        #    Use bytes to avoid Windows \r\n corruption in the filename
        tree_input = f"100644 blob {blob_sha}\tindex.html\n".encode("utf-8")
        result = subprocess.run(
            ["git", "mktree"],
            input=tree_input,
            capture_output=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git mktree failed: {result.stderr.decode().strip()}")
        tree_sha = result.stdout.decode().strip()

        # 5. Create commit (with parent if gh-pages already exists)
        commit_msg = f"Update analytics dashboard ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        commit_cmd = ["git", "commit-tree", tree_sha, "-m", commit_msg]

        try:
            parent_sha = _run_git("rev-parse", "refs/heads/gh-pages")
            commit_cmd.extend(["-p", parent_sha])
        except RuntimeError:
            pass  # First commit -- no parent

        result = subprocess.run(
            commit_cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git commit-tree failed: {result.stderr.strip()}")
        commit_sha = result.stdout.strip()

        # 6. Update gh-pages ref
        _run_git("update-ref", "refs/heads/gh-pages", commit_sha)

        # 7. Push to origin
        _run_git("push", "origin", "gh-pages")

        if verbose:
            print(f"Dashboard published to {PAGES_URL}")

        log.info(f"Dashboard published to gh-pages ({commit_sha[:8]})")
        return True

    finally:
        # 8. Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def enable_github_pages() -> bool:
    """
    Enable GitHub Pages on the repository using the gh-pages branch.
    Idempotent -- handles 'already enabled' gracefully.

    Returns True if Pages is enabled (or was already), False on failure.
    """
    try:
        _run_gh(
            "api",
            f"repos/{OWNER}/{REPO}/pages",
            "-X", "POST",
            "-f", "build_type=legacy",
            "-f", "source[branch]=gh-pages",
            "-f", "source[path]=/",
        )
        print(f"GitHub Pages enabled at {PAGES_URL}")
        return True
    except RuntimeError as e:
        err = str(e)
        if "already" in err.lower() or "409" in err:
            print(f"GitHub Pages already enabled at {PAGES_URL}")
            return True
        raise
