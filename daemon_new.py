"""
Auto-Grading Daemon - New Architecture

Polls Canvas for all "Hands-on" assignments, queues submissions FIFO,
clones repos, and grades with AI.
"""

import asyncio
import os
import signal
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import new modules
from canvas import CanvasClient, parse_submission
from assignments import (
    create_assignment_structure,
    create_submission_structure,
    cleanup_old_repos,
    list_all_assignments,
    save_grading_result,
    load_config
)
from repo_cloner import clone_repo, has_gh_cli
from submission_queue import (
    add_to_queue,
    get_next,
    mark_completed,
    mark_failed,
    get_status as get_queue_status
)
from grader_new import grade_with_copilot, grade_mock

console = Console()

# Global flag for graceful shutdown
shutdown_flag = False


def handle_signal(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_flag
    console.print("\n[yellow]⚠ Shutdown signal received. Finishing current task...[/yellow]")
    shutdown_flag = True


def sync_assignments():
    """
    Fetch all assignments from Canvas and create folder structure.
    
    Only syncs assignments matching the filter keyword.
    """
    config = load_config()
    filter_keyword = config.get("grading", {}).get("assignment_filter", "")
    
    console.print(f"\n[cyan]🔄 Syncing assignments (filter: '{filter_keyword}')...[/cyan]")
    
    client = CanvasClient()
    assignments = client.get_all_assignments(filter_keyword)
    
    console.print(f"[green]✓[/green] Found {len(assignments)} matching assignments")
    
    for assignment in assignments:
        assignment_id = str(assignment["id"])
        assignment_title = assignment["name"]
        
        assignment_data = {
            "id": assignment_id,
            "name": assignment_title,
            "points_possible": assignment.get("points_possible", 1),
            "due_at": assignment.get("due_at"),
            "synced_at": datetime.now().isoformat()
        }
        
        create_assignment_structure(assignment_id, assignment_title, assignment_data)
    
    return assignments


def poll_submissions():
    """
    Poll Canvas for new submissions across all synced assignments.
    
    Adds new submissions to the queue.
    """
    config = load_config()
    filter_keyword = config.get("grading", {}).get("assignment_filter", "")
    
    console.print("\n[cyan]📥 Polling for new submissions...[/cyan]")
    
    client = CanvasClient()
    assignments = client.get_all_assignments(filter_keyword)
    
    new_count = 0
    
    for assignment in assignments:
        assignment_id = str(assignment["id"])
        assignment_title = assignment["name"]
        
        # Get submissions for this assignment
        raw_submissions = client.get_submissions(assignment_id)
        
        for raw_sub in raw_submissions:
            parsed = parse_submission(raw_sub)
            if parsed:
                # Get student login
                student_login = raw_sub.get("user", {}).get("login_id") or raw_sub.get("user", {}).get("name", "unknown")
                
                # Add to queue (will skip if already queued/completed)
                item_id = add_to_queue(
                    assignment_id,
                    assignment_title,
                    student_login,
                    parsed
                )
                
                # Check if it was actually added (new)
                queue_status = get_queue_status()
                for item in queue_status["pending_items"]:
                    if item["id"] == item_id and item.get("queued_at"):
                        # Just added
                        new_count += 1
                        break
    
    if new_count > 0:
        console.print(f"[green]✓[/green] Added {new_count} new submissions to queue")
    else:
        console.print("[dim]No new submissions[/dim]")
    
    return new_count


async def process_one():
    """
    Process one submission from the queue.
    
    Returns True if something was processed, False if queue was empty.
    """
    # Get next item from queue
    item = get_next()
    
    if not item:
        return False  # Queue empty
    
    assignment_id = item["assignment_id"]
    assignment_title = item["assignment_title"]
    student_login = item["student_login"]
    submission_type = item["submission_type"]
    submission_url = item["submission_url"]
    
    console.print(f"\n[yellow]⚙ Processing:[/yellow] {student_login} - {assignment_title}")
    
    # Create submission folder structure
    paths = create_submission_structure(assignment_id, assignment_title, student_login)
    
    # Clone repo if GitHub submission
    if submission_type == "github":
        console.print(f"[cyan]  → Cloning repository...[/cyan]")
        
        if not has_gh_cli():
            error_msg = "GitHub CLI (gh) not installed"
            console.print(f"[red]  ✗ {error_msg}[/red]")
            mark_failed(item["id"], error_msg)
            return True
        
        clone_result = clone_repo(submission_url, paths["repo"])
        
        if not clone_result["success"]:
            error_msg = clone_result["error"]
            console.print(f"[red]  ✗ Clone failed: {error_msg}[/red]")
            mark_failed(item["id"], error_msg)
            return True
        
        console.print(f"[green]  ✓ Cloned successfully[/green]")
    
    # Grade with AI or mock
    console.print(f"[cyan]  → Grading...[/cyan]")
    
    # Get assignment metadata for max points
    from pathlib import Path
    import json
    assignment_folder = paths["base"].parent.parent
    assignment_json = assignment_folder / "assignment.json"
    
    max_points = 1  # Default
    if assignment_json.exists():
        with open(assignment_json, "r") as f:
            metadata = json.load(f)
            max_points = metadata.get("points_possible", 1)
    
    # Check if we should use mock or AI
    use_mock = os.environ.get("USE_MOCK", "false").lower() == "true"
    
    if use_mock:
        result = grade_mock(assignment_title, max_points, submission_type)
    else:
        result = await grade_with_copilot(
            assignment_id,
            assignment_title,
            max_points,
            student_login,
            submission_type,
            submission_url,
            paths["repo"],
            paths["files"]
        )
    
    if result["success"]:
        # Save grading result
        submission_data = {
            "id": item["submission_id"],
            "type": submission_type,
            "url": submission_url
        }
        
        grading_file = save_grading_result(
            assignment_id,
            assignment_title,
            student_login,
            submission_data,
            result["score"],
            result["feedback"]
        )
        
        mark_completed(item["id"], result["score"], str(grading_file))
        console.print(f"[green]  ✓ Graded: {result['score']}/{max_points}[/green]")
    else:
        mark_failed(item["id"], result["error"])
        console.print(f"[red]  ✗ Grading failed: {result['error']}[/red]")
    
    return True


def show_status():
    """Display queue status in a rich table."""
    queue_status = get_queue_status()
    
    # Create status panel
    status_text = f"""
Pending: [yellow]{queue_status['pending_count']}[/yellow]
Processing: [cyan]{1 if queue_status['processing'] else 0}[/cyan]
Completed: [green]{queue_status['completed_count']}[/green]
Failed: [red]{queue_status['failed_count']}[/red]
"""
    
    panel = Panel(
        status_text,
        title="📊 Queue Status",
        border_style="blue"
    )
    console.print(panel)
    
    # Show currently processing
    if queue_status['processing']:
        item = queue_status['processing']
        console.print(f"\n[cyan]Currently Processing:[/cyan]")
        console.print(f"  {item['student_login']} - {item['assignment_title']}")
    
    # Show pending queue (first 5)
    if queue_status['pending_items']:
        console.print(f"\n[yellow]Pending Queue (showing first 5):[/yellow]")
        for item in queue_status['pending_items'][:5]:
            console.print(f"  • {item['student_login']} - {item['assignment_title']}")
        
        if len(queue_status['pending_items']) > 5:
            console.print(f"  ... and {len(queue_status['pending_items']) - 5} more")


async def run_daemon(mock: bool = True):
    """
    Run the grading daemon.
    
    Workflow:
    1. Sync assignments from Canvas
    2. Poll for new submissions
    3. Process queue FIFO
    4. Cleanup old repos
    5. Sleep and repeat
    """
    global shutdown_flag
    
    # Set mock mode
    import os
    os.environ["USE_MOCK"] = "true" if mock else "false"
    
    # Setup signal handler
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    console.print("[bold cyan]🤖 Canvas Auto-Grading Daemon[/bold cyan]")
    console.print(f"Mode: {'[yellow]Mock[/yellow]' if mock else '[green]AI[/green]'}\n")
    
    # Initial sync
    sync_assignments()
    
    config = load_config()
    poll_interval = config.get("daemon", {}).get("poll_interval_seconds", 300)
    cleanup_days = config.get("grading", {}).get("cleanup_days", 7)
    
    cycle = 1
    
    while not shutdown_flag:
        console.print(f"\n[bold]═══ Cycle {cycle} ═══[/bold]")
        
        # Poll for new submissions
        poll_submissions()
        
        # Import retry functions
        from submission_queue import get_retryable_failed, retry_all_eligible
        
        # Process queue until empty
        processed_count = 0
        while not shutdown_flag:
            did_process = await process_one()
            if not did_process:
                break  # Queue empty
            processed_count += 1
        
        if processed_count > 0:
            console.print(f"\n[green]✓ Processed {processed_count} submissions[/green]")
        
        # Auto-retry failed submissions (WinError 5 retries infinitely, others max 1 retry)
        retryable = get_retryable_failed(max_retries=1)
        if retryable:
            console.print(f"\n[yellow]🔄 Retrying {len(retryable)} failed submission(s)...[/yellow]")
            
            # Clean locked repo folders before retry
            import subprocess
            import time
            cleaned_count = 0
            
            for item in retryable:
                error = item.get("last_error", item.get("error", ""))
                if "WinError 5" in error or "Access is denied" in error:
                    # File lock error - clean the repo folder forcefully
                    from assignments import get_submission_folder
                    repo_path = get_submission_folder(
                        item["assignment_id"],
                        item["assignment_title"],
                        item["student_login"]
                    ) / "repo"
                    
                    if repo_path.exists():
                        try:
                            # Use PowerShell Remove-Item -Force -Recurse for Windows file locks
                            subprocess.run(
                                ["powershell", "-Command", f"Remove-Item -Path '{repo_path}' -Recurse -Force -ErrorAction SilentlyContinue"],
                                capture_output=True,
                                timeout=10
                            )
                            cleaned_count += 1
                        except Exception as e:
                            console.print(f"[dim]  Could not clean {item['student_login']}: {e}[/dim]")
            
            if cleaned_count > 0:
                console.print(f"[dim]  Cleaned {cleaned_count} locked folder(s)[/dim]")
                # Brief sleep to let Windows release file handles
                time.sleep(2)
            
            # Move failed items back to pending queue
            retried_count = retry_all_eligible(max_retries=1)
            console.print(f"[green]✓ Moved {retried_count} item(s) back to queue[/green]")
            
            # Process retry queue
            console.print("[cyan]📋 Processing retries...[/cyan]")
            retry_processed = 0
            while not shutdown_flag:
                did_process = await process_one()
                if not did_process:
                    break
                retry_processed += 1
            
            if retry_processed > 0:
                console.print(f"[green]✓ Processed {retry_processed} retry(ies)[/green]")
        
        # Show permanent failures (max retries exhausted)
        queue_status = get_queue_status()
        if queue_status["failed_items"]:
            console.print(f"\n[red]❌ {len(queue_status['failed_items'])} submission(s) require human review:[/red]")
            for item in queue_status["failed_items"][:5]:
                error = item.get("error", item.get("last_error", "Unknown error"))
                retry_count = item.get("retry_count", 0)
                console.print(f"  • {item['student_login']}: {error} (attempts: {retry_count + 1})")
            if len(queue_status["failed_items"]) > 5:
                console.print(f"  ... and {len(queue_status['failed_items']) - 5} more")
        
        # Cleanup old repos
        if cycle % 10 == 0:  # Every 10 cycles
            console.print(f"\n[cyan]🧹 Cleaning up repos older than {cleanup_days} days...[/cyan]")
            deleted = cleanup_old_repos(cleanup_days)
            if deleted > 0:
                console.print(f"[green]✓ Deleted {deleted} old repos[/green]")
        
        # Show status
        show_status()
        
        if shutdown_flag:
            break
        
        # Sleep
        console.print(f"\n[dim]💤 Sleeping for {poll_interval} seconds...[/dim]")
        
        for _ in range(poll_interval):
            if shutdown_flag:
                break
            time.sleep(1)
        
        cycle += 1
    
    console.print("\n[green]✓ Daemon stopped gracefully[/green]")


if __name__ == "__main__":
    import sys
    
    mock = "--no-mock" not in sys.argv
    
    asyncio.run(run_daemon(mock))
