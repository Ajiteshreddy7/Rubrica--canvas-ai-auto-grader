"""
Auto-Grading Daemon - New Architecture

Polls Canvas for all "Hands-on" assignments, queues submissions FIFO,
clones repos, and grades with AI.
"""

import asyncio
import json
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import load_config
from canvas import CanvasClient, parse_submission, format_rubric_as_markdown
from assignments import (
    create_assignment_structure,
    create_submission_structure,
    cleanup_old_repos,
    list_all_assignments,
    save_grading_result,
    get_submission_folder,
    get_assignment_folder,
)
from repo_cloner import clone_repo, has_gh_cli
from submission_queue import (
    add_to_queue,
    get_next,
    mark_completed,
    mark_failed,
    get_status as get_queue_status,
    get_retryable_failed,
    retry_all_eligible
)
from grader_new import grade_with_copilot, grade_mock
from logger import log

console = Console()

# Global flag for graceful shutdown
shutdown_flag = False


def handle_signal(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_flag
    console.print("\n[yellow]! Shutdown signal received. Finishing current task...[/yellow]")
    shutdown_flag = True


def sync_assignments(assignment_names=None):
    """
    Fetch all assignments from Canvas and create folder structure.

    Args:
        assignment_names: Optional list of assignment name substrings to filter by.
                         Overrides config filter when provided.
    """
    config = load_config()
    filter_keyword = assignment_names if assignment_names else config.grading.assignment_filter

    console.print(f"\n[cyan]>> Syncing assignments (filter: '{filter_keyword}')...[/cyan]")
    log.info(f"Syncing assignments (filter: '{filter_keyword}')")

    client = CanvasClient()
    assignments = client.get_all_assignments(filter_keyword)

    console.print(f"[green][OK][/green] Found {len(assignments)} matching assignments")
    log.info(f"Found {len(assignments)} matching assignments")
    
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

        # Fetch and save rubric from Canvas if available
        try:
            detailed = client.get_assignment_with_rubric(assignment_id)
            if "rubric" in detailed:
                rubric_md = format_rubric_as_markdown(
                    detailed["rubric"],
                    assignment.get("points_possible", 1)
                )
                rubric_path = get_assignment_folder(assignment_id, assignment_title) / "rubric.md"
                rubric_path.write_text(rubric_md, encoding="utf-8")
                console.print(f"  [green][OK][/green] Rubric saved for {assignment_title}")
        except Exception as e:
            console.print(f"  [dim]No rubric found for {assignment_title}: {e}[/dim]")

    return assignments


def poll_submissions(assignment_names=None):
    """
    Poll Canvas for new submissions across all synced assignments.

    Args:
        assignment_names: Optional list of assignment name substrings to filter by.
                         Overrides config filter when provided.

    Adds new submissions to the queue.
    """
    config = load_config()
    filter_keyword = assignment_names if assignment_names else config.grading.assignment_filter

    console.print("\n[cyan]>> Polling for new submissions...[/cyan]")
    log.info("Polling for new submissions")
    
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
        console.print(f"[green][OK][/green] Added {new_count} new submissions to queue")
        log.info(f"Added {new_count} new submissions to queue")
    else:
        console.print("[dim]No new submissions[/dim]")
        log.info("No new submissions")
    
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
    
    console.print(f"\n[yellow]> Processing:[/yellow] {student_login} - {assignment_title}")
    log.info(f"Processing: {student_login} - {assignment_title}")
    
    # Create submission folder structure
    paths = create_submission_structure(assignment_id, assignment_title, student_login)
    
    # Clone repo if GitHub submission
    if submission_type == "github":
        console.print(f"[cyan]  > Cloning repository...[/cyan]")
        
        if not has_gh_cli():
            error_msg = "GitHub CLI (gh) not installed"
            console.print(f"[red]  [FAIL] {error_msg}[/red]")
            mark_failed(item["id"], error_msg)
            return True
        
        clone_result = clone_repo(submission_url, paths["repo"])
        
        if not clone_result["success"]:
            error_msg = clone_result["error"]
            console.print(f"[red]  [FAIL] Clone failed: {error_msg}[/red]")
            log.error(f"Clone failed for {student_login}: {error_msg}")
            mark_failed(item["id"], error_msg)
            return True
        
        console.print(f"[green]  [OK] Cloned successfully[/green]")
    
    # Grade with AI or mock
    console.print(f"[cyan]  > Grading...[/cyan]")
    
    # Get assignment metadata for max points
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
        console.print(f"[green]  [OK] Graded: {result['score']}/{max_points}[/green]")
        log.info(f"Graded {student_login}: {result['score']}/{max_points}")

        # Post grade to Canvas if enabled
        config = load_config()
        if config.grading.post_to_canvas:
            try:
                client = CanvasClient()
                # Get user_id from the submission data
                user_id = item.get("submission_id", "")
                if user_id:
                    client.post_grade(
                        assignment_id,
                        user_id,
                        result["score"],
                        comment=f"AI-graded: {result['score']}/{max_points}"
                    )
                    console.print(f"[green]  [OK] Posted grade to Canvas[/green]")
            except Exception as e:
                console.print(f"[yellow]  ! Could not post to Canvas: {e}[/yellow]")
    else:
        mark_failed(item["id"], result["error"])
        console.print(f"[red]  [FAIL] Grading failed: {result['error']}[/red]")
        log.error(f"Grading failed for {student_login}: {result['error']}")
    
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
        title="Queue Status",
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
            console.print(f"  - {item['student_login']} - {item['assignment_title']}")
        
        if len(queue_status['pending_items']) > 5:
            console.print(f"  ... and {len(queue_status['pending_items']) - 5} more")


async def run_daemon(mock: bool = True, assignment_names=None):
    """
    Run the grading daemon.

    Args:
        mock: If True, use mock grading instead of real AI.
        assignment_names: Optional list of assignment name substrings to scope the daemon to.
                         Overrides config filter when provided.

    Workflow:
    1. Sync assignments from Canvas
    2. Poll for new submissions
    3. Process queue FIFO
    4. Cleanup old repos
    5. Sleep and repeat
    """
    global shutdown_flag

    # Set mock mode
    os.environ["USE_MOCK"] = "true" if mock else "false"

    # Setup signal handler
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    console.print("[bold cyan]Rubrica[/bold cyan]")
    console.print(f"Mode: {'[yellow]Mock[/yellow]' if mock else '[green]AI[/green]'}\n")
    if assignment_names:
        console.print(f"Scoped to: {', '.join(assignment_names)}\n")
    log.info(f"Daemon started (mode: {'mock' if mock else 'AI'})")

    # Initial sync
    sync_assignments(assignment_names)
    
    config = load_config()
    poll_interval = config.daemon.poll_interval_seconds
    cleanup_days = config.grading.cleanup_days
    
    cycle = 1
    
    while not shutdown_flag:
        console.print(f"\n[bold]=== Cycle {cycle} ===[/bold]")
        log.info(f"=== Cycle {cycle} ===")
        
        # Poll for new submissions
        poll_submissions(assignment_names)
        
        # Process queue until empty
        processed_count = 0
        while not shutdown_flag:
            did_process = await process_one()
            if not did_process:
                break  # Queue empty
            processed_count += 1
        
        if processed_count > 0:
            console.print(f"\n[green][OK] Processed {processed_count} submissions[/green]")
            log.info(f"Processed {processed_count} submissions")
        
        # Auto-retry failed submissions (WinError 5 retries infinitely, others max 1 retry)
        retryable = get_retryable_failed(max_retries=1)
        if retryable:
            console.print(f"\n[yellow]>> Retrying {len(retryable)} failed submission(s)...[/yellow]")
            log.warning(f"Retrying {len(retryable)} failed submission(s)")
            
            # Clean locked repo folders before retry
            cleaned_count = 0

            for item in retryable:
                error = item.get("last_error", item.get("error", ""))
                if "WinError 5" in error or "Access is denied" in error:
                    # File lock error - clean the repo folder forcefully
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
                await asyncio.sleep(2)
            
            # Move failed items back to pending queue
            retried_count = retry_all_eligible(max_retries=1)
            console.print(f"[green][OK] Moved {retried_count} item(s) back to queue[/green]")
            
            # Process retry queue
            console.print("[cyan]>> Processing retries...[/cyan]")
            retry_processed = 0
            while not shutdown_flag:
                did_process = await process_one()
                if not did_process:
                    break
                retry_processed += 1
            
            if retry_processed > 0:
                console.print(f"[green][OK] Processed {retry_processed} retry(ies)[/green]")
        
        # Show permanent failures (max retries exhausted)
        queue_status = get_queue_status()
        if queue_status["failed_items"]:
            console.print(f"\n[red]X {len(queue_status['failed_items'])} submission(s) require human review:[/red]")
            log.error(f"{len(queue_status['failed_items'])} submission(s) require human review")
            for item in queue_status["failed_items"][:5]:
                error = item.get("error", item.get("last_error", "Unknown error"))
                retry_count = item.get("retry_count", 0)
                console.print(f"  - {item['student_login']}: {error} (attempts: {retry_count + 1})")
            if len(queue_status["failed_items"]) > 5:
                console.print(f"  ... and {len(queue_status['failed_items']) - 5} more")
        
        # Cleanup old repos
        if cycle % 10 == 0:  # Every 10 cycles
            console.print(f"\n[cyan]>> Cleaning up repos older than {cleanup_days} days...[/cyan]")
            deleted = cleanup_old_repos(cleanup_days)
            if deleted > 0:
                console.print(f"[green][OK] Deleted {deleted} old repos[/green]")
        
        # Show status
        show_status()

        # Auto-publish analytics dashboard
        from publish import publish_dashboard
        try:
            if publish_dashboard(verbose=False):
                console.print("[dim]Dashboard published to GitHub Pages[/dim]")
        except Exception as e:
            log.warning(f"Dashboard publish skipped: {e}")

        if shutdown_flag:
            break
        
        # Sleep
        console.print(f"\n[dim]Sleeping for {poll_interval} seconds...[/dim]")
        
        for _ in range(poll_interval):
            if shutdown_flag:
                break
            await asyncio.sleep(1)
        
        cycle += 1
    
    console.print("\n[green][OK] Daemon stopped gracefully[/green]")
    log.info("Daemon stopped gracefully")


async def run_grade(mock: bool, assignments_with_students, regrade: bool = False):
    """
    One-shot grading: process selected submissions directly, then exit.

    Bypasses the shared pending queue so it never interferes with a running
    daemon or other queued items.

    Args:
        mock: If True, use mock grading.
        assignments_with_students: List of dicts, each with keys:
            - assignment: raw Canvas assignment dict
            - students: list of (student_login, parsed_submission) tuples
        regrade: If True, re-grade submissions that already have a grading.md.
    """
    os.environ["USE_MOCK"] = "true" if mock else "false"

    total = sum(len(a["students"]) for a in assignments_with_students)
    console.print(f"\nGrading {total} submission(s)...\n")
    log.info(f"One-shot grade: {total} submissions (mode: {'mock' if mock else 'AI'})")

    processed = 0
    failed_count = 0
    skipped_count = 0

    for entry in assignments_with_students:
        assignment = entry["assignment"]
        assignment_id = str(assignment["id"])
        assignment_title = assignment["name"]
        max_points = assignment.get("points_possible", 1)

        # Ensure folder structure
        assignment_data = {
            "id": assignment_id,
            "name": assignment_title,
            "points_possible": max_points,
            "due_at": assignment.get("due_at"),
            "synced_at": datetime.now().isoformat(),
        }
        create_assignment_structure(assignment_id, assignment_title, assignment_data)

        for student_login, parsed in entry["students"]:
            submission_type = parsed.get("type", "unknown")
            submission_url = parsed.get("url", "")
            submission_id = parsed.get("id", "")

            # Check if already graded
            sub_folder = get_submission_folder(assignment_id, assignment_title, student_login)
            grading_file = sub_folder / "grading.md"
            if grading_file.exists() and not regrade:
                console.print(f"  [dim]Skipped (already graded): {student_login} - {assignment_title}[/dim]")
                skipped_count += 1
                continue

            console.print(f"\n[yellow]> Processing:[/yellow] {student_login} - {assignment_title}")
            log.info(f"Processing: {student_login} - {assignment_title}")

            try:
                paths = create_submission_structure(assignment_id, assignment_title, student_login)

                # Clone repo if GitHub submission
                if submission_type == "github":
                    console.print("[cyan]  > Cloning repository...[/cyan]")
                    if not has_gh_cli():
                        console.print("[red]  [FAIL] GitHub CLI (gh) not installed[/red]")
                        failed_count += 1
                        continue
                    clone_result = clone_repo(submission_url, paths["repo"])
                    if not clone_result["success"]:
                        console.print(f"[red]  [FAIL] Clone failed: {clone_result['error']}[/red]")
                        log.error(f"Clone failed for {student_login}: {clone_result['error']}")
                        failed_count += 1
                        continue
                    console.print("[green]  [OK] Cloned successfully[/green]")

                # Grade
                console.print("[cyan]  > Grading...[/cyan]")

                use_mock = os.environ.get("USE_MOCK", "false").lower() == "true"
                if use_mock:
                    result = grade_mock(assignment_title, max_points, submission_type)
                else:
                    result = await grade_with_copilot(
                        assignment_id, assignment_title, max_points,
                        student_login, submission_type, submission_url,
                        paths["repo"], paths["files"],
                    )

                if result["success"]:
                    submission_data = {
                        "id": submission_id,
                        "type": submission_type,
                        "url": submission_url,
                    }
                    save_grading_result(
                        assignment_id, assignment_title, student_login,
                        submission_data, result["score"], result["feedback"],
                    )
                    console.print(f"[green]  [OK] Graded: {result['score']}/{max_points}[/green]")
                    log.info(f"Graded {student_login}: {result['score']}/{max_points}")

                    # Post grade to Canvas if enabled
                    config = load_config()
                    if config.grading.post_to_canvas:
                        try:
                            client = CanvasClient()
                            if submission_id:
                                client.post_grade(
                                    assignment_id, submission_id, result["score"],
                                    comment=f"AI-graded: {result['score']}/{max_points}",
                                )
                                console.print("[green]  [OK] Posted grade to Canvas[/green]")
                        except Exception as e:
                            console.print(f"[yellow]  ! Could not post to Canvas: {e}[/yellow]")

                    processed += 1
                else:
                    console.print(f"[red]  [FAIL] Grading failed: {result['error']}[/red]")
                    log.error(f"Grading failed for {student_login}: {result['error']}")
                    failed_count += 1

            except Exception as e:
                console.print(f"[red]  [FAIL] Error: {e}[/red]")
                log.error(f"Unexpected error grading {student_login}: {e}")
                failed_count += 1

    console.print(f"\n[green][OK] Finished. Processed {processed} submission(s).[/green]")
    if skipped_count:
        console.print(f"[dim]{skipped_count} already graded (skipped).[/dim]")
    if failed_count:
        console.print(f"[red]{failed_count} submission(s) failed.[/red]")
    log.info(f"One-shot grade finished: processed {processed}, skipped {skipped_count}, failed {failed_count}")

    # Auto-publish analytics dashboard
    from publish import publish_dashboard
    try:
        console.print("\n[cyan]>> Publishing analytics dashboard...[/cyan]")
        if publish_dashboard():
            console.print("[green][OK] Dashboard published to GitHub Pages[/green]")
    except Exception as e:
        console.print(f"[yellow]Dashboard publish skipped: {e}[/yellow]")


if __name__ == "__main__":
    print("Use 'python cli.py run' instead.")
    print("Run 'python cli.py --help' for all commands.")
