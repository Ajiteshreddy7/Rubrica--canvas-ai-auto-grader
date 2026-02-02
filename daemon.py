#!/usr/bin/env python3
"""
Grading Agent Daemon

CLI daemon that polls Canvas for new submissions, stages them,
and auto-grades one submission per 5-minute cycle.

Usage:
    python daemon.py run          # Start the daemon
    python daemon.py status       # Show submission summary
    python daemon.py retry <id>   # Reset failed submission to pending
    python daemon.py grade <id>   # Manually grade a specific submission
    python daemon.py init         # Initialize config and directories
"""

import click
import time
import signal
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Local imports
from state import (
    load_status,
    get_next_pending,
    get_status_summary,
    add_submission,
    mark_grading,
    mark_graded,
    mark_failed,
    reset_to_pending,
    get_submission,
    update_assignment_info
)
from canvas import fetch_new_submissions, CanvasClient
from grader import grade_submission

# Constants
POLL_INTERVAL = 300  # 5 minutes
console = Console()

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    shutdown_requested = True
    console.print("\n[yellow]🛑 Shutdown requested. Finishing current operation...[/yellow]")


def log_timestamp():
    """Print a timestamp line."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[dim]─── {now} ───[/dim]")


def log_info(message: str):
    """Log an info message."""
    console.print(f"[blue]ℹ[/blue]  {message}")


def log_success(message: str):
    """Log a success message."""
    console.print(f"[green]✓[/green]  {message}")


def log_warning(message: str):
    """Log a warning message."""
    console.print(f"[yellow]⚠[/yellow]  {message}")


def log_error(message: str):
    """Log an error message."""
    console.print(f"[red]✗[/red]  {message}")


def log_staging(student: str, sub_type: str):
    """Log a new submission being staged."""
    console.print(f"[yellow]📥[/yellow] Staged: [cyan]{student}[/cyan] ({sub_type})")


def log_grading_start(student: str):
    """Log grading start."""
    console.print(f"[blue]📝[/blue] Grading: [cyan]{student}[/cyan]...")


def log_grading_complete(student: str, score: float, max_points: int):
    """Log grading completion."""
    percentage = (score / max_points) * 100 if max_points > 0 else 0
    color = "green" if percentage >= 70 else "yellow" if percentage >= 50 else "red"
    console.print(f"[green]✓[/green]  Graded: [cyan]{student}[/cyan] - [{color}]{score}/{max_points}[/{color}]")


def log_grading_failed(student: str, error: str):
    """Log grading failure."""
    console.print(f"[red]✗[/red]  Failed: [cyan]{student}[/cyan] - {error}")


def poll_and_stage():
    """Poll Canvas for new submissions and stage them."""
    try:
        status = load_status()
        existing_ids = [s["id"] for s in status["submissions"]]
        
        new_submissions = fetch_new_submissions(existing_ids)
        
        for sub in new_submissions:
            add_submission(
                submission_id=sub["id"],
                student=sub["student"],
                submission_type=sub["type"],
                url=sub["url"]
            )
            log_staging(sub["student"], sub["type"])
        
        if new_submissions:
            log_info(f"Staged {len(new_submissions)} new submission(s)")
        
        return len(new_submissions)
    
    except Exception as e:
        log_error(f"Error polling Canvas: {str(e)}")
        return 0


def process_one_submission(use_mock: bool = True):
    """Process the next pending submission."""
    submission = get_next_pending()
    
    if not submission:
        return None
    
    student = submission["student"]
    log_grading_start(student)
    
    # Mark as grading
    mark_grading(submission["id"])
    
    try:
        # Grade the submission
        result = grade_submission(submission, use_mock=use_mock)
        
        if result["success"]:
            # Mark as graded
            mark_graded(
                submission["id"],
                result["score"],
                result["grading_file"]
            )
            
            status = load_status()
            log_grading_complete(student, result["score"], status["maxPoints"])
            return {"success": True, "student": student, "score": result["score"]}
        else:
            raise Exception("Grading returned unsuccessful result")
    
    except Exception as e:
        # Mark as failed
        error_msg = str(e)[:200]  # Truncate long errors
        mark_failed(submission["id"], error_msg)
        log_grading_failed(student, error_msg)
        return {"success": False, "student": student, "error": error_msg}


def print_status_table():
    """Print a table of all submissions and their status."""
    status = load_status()
    
    # Header panel
    assignment = status.get("assignment", "Not configured")
    max_points = status.get("maxPoints", 100)
    
    console.print(Panel(
        f"[bold]{assignment}[/bold]\nMax Points: {max_points}",
        title="📋 Assignment",
        box=box.ROUNDED
    ))
    
    # Summary
    summary = get_status_summary()
    summary_text = Text()
    summary_text.append(f"Total: {summary['total']}  ", style="bold")
    summary_text.append(f"Pending: {summary['pending']}  ", style="yellow")
    summary_text.append(f"Graded: {summary['graded']}  ", style="green")
    summary_text.append(f"Failed: {summary['failed']}", style="red")
    console.print(summary_text)
    console.print()
    
    # Table
    if not status["submissions"]:
        console.print("[dim]No submissions yet[/dim]")
        return
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("Student", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Score")
    table.add_column("Staged At", style="dim")
    
    for sub in status["submissions"]:
        # Status badge
        status_str = sub["status"]
        if status_str == "pending":
            status_badge = "[yellow]● pending[/yellow]"
        elif status_str == "grading":
            status_badge = "[blue]● grading[/blue]"
        elif status_str == "graded":
            status_badge = "[green]● graded[/green]"
        elif status_str == "failed":
            status_badge = "[red]● failed[/red]"
        else:
            status_badge = status_str
        
        # Score
        score_str = ""
        if sub["score"] is not None:
            score_str = f"{sub['score']}/{max_points}"
        elif sub["status"] == "failed":
            score_str = f"[dim]{sub.get('error', 'Error')[:20]}...[/dim]"
        
        # Staged time
        staged = sub.get("stagedAt", "")
        if staged:
            staged = staged.split("T")[0]  # Just the date
        
        table.add_row(
            sub["id"][:8],
            sub["student"][:20],
            sub["type"],
            status_badge,
            score_str,
            staged
        )
    
    console.print(table)


def run_daemon(use_mock: bool = True):
    """Run the main daemon loop."""
    global shutdown_requested
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print startup banner
    console.print(Panel(
        "[bold green]Grading Agent Daemon[/bold green]\n"
        f"Polling every {POLL_INTERVAL // 60} minutes\n"
        "Press Ctrl+C to stop",
        box=box.DOUBLE
    ))
    
    cycle_count = 0
    
    while not shutdown_requested:
        cycle_count += 1
        log_timestamp()
        log_info(f"Cycle {cycle_count}")
        
        # Poll for new submissions
        new_count = poll_and_stage()
        
        # Process one pending submission
        result = process_one_submission(use_mock=use_mock)
        
        if result is None:
            log_info("No pending submissions")
        
        # Show summary
        summary = get_status_summary()
        log_info(
            f"Status: {summary['pending']} pending, "
            f"{summary['graded']} graded, "
            f"{summary['failed']} failed"
        )
        
        # Wait for next cycle
        if not shutdown_requested:
            console.print(f"[dim]Sleeping for {POLL_INTERVAL // 60} minutes...[/dim]")
            
            # Sleep in small intervals to check shutdown flag
            for _ in range(POLL_INTERVAL):
                if shutdown_requested:
                    break
                time.sleep(1)
    
    # Shutdown summary
    console.print()
    log_warning("Daemon stopped")
    print_status_table()


# CLI Commands
@click.group()
def cli():
    """Grading Agent Daemon - Auto-grade Canvas submissions."""
    pass


@cli.command()
@click.option("--mock/--no-mock", default=True, help="Use mock grading (no Copilot SDK)")
def run(mock):
    """Start the daemon (polls every 5 minutes)."""
    run_daemon(use_mock=mock)


@cli.command()
def status():
    """Show submission status summary."""
    print_status_table()


@cli.command()
@click.argument("submission_id")
def retry(submission_id):
    """Reset a failed submission to pending."""
    # Find submission by partial ID match
    status = load_status()
    found = None
    
    for sub in status["submissions"]:
        if sub["id"].startswith(submission_id):
            found = sub
            break
    
    if not found:
        log_error(f"Submission not found: {submission_id}")
        return
    
    if found["status"] != "failed":
        log_warning(f"Submission is not failed (status: {found['status']})")
        return
    
    if reset_to_pending(found["id"]):
        log_success(f"Reset submission {found['id'][:8]} to pending")
    else:
        log_error("Failed to reset submission")


@cli.command()
@click.argument("submission_id")
@click.option("--mock/--no-mock", default=True, help="Use mock grading")
def grade(submission_id, mock):
    """Manually grade a specific submission."""
    # Find submission
    status = load_status()
    found = None
    
    for sub in status["submissions"]:
        if sub["id"].startswith(submission_id):
            found = sub
            break
    
    if not found:
        log_error(f"Submission not found: {submission_id}")
        return
    
    log_grading_start(found["student"])
    mark_grading(found["id"])
    
    try:
        result = grade_submission(found, use_mock=mock)
        
        if result["success"]:
            mark_graded(found["id"], result["score"], result["grading_file"])
            log_grading_complete(found["student"], result["score"], status["maxPoints"])
        else:
            raise Exception("Grading failed")
    
    except Exception as e:
        mark_failed(found["id"], str(e)[:200])
        log_grading_failed(found["student"], str(e))


@cli.command()
@click.option("--assignment", prompt="Assignment name", help="Name of the assignment")
@click.option("--max-points", prompt="Max points", type=int, help="Maximum points")
def init(assignment, max_points):
    """Initialize the grading agent configuration."""
    # Update assignment info
    update_assignment_info(assignment, max_points)
    
    # Create directories
    submissions_dir = Path(__file__).parent / "submissions"
    submissions_dir.mkdir(exist_ok=True)
    
    log_success(f"Initialized assignment: {assignment} ({max_points} points)")
    log_info("Edit config.json to add your Canvas API credentials")
    log_info("Edit rubric.md to customize the grading rubric")


@cli.command()
@click.argument("student")
@click.argument("submission_type", type=click.Choice(["github", "pdf", "text", "url"]))
@click.argument("url")
def add(student, submission_type, url):
    """Manually add a submission for testing."""
    import uuid
    
    submission_id = str(uuid.uuid4())[:8]
    
    sub = add_submission(
        submission_id=submission_id,
        student=student,
        submission_type=submission_type,
        url=url
    )
    
    log_success(f"Added submission: {sub['id']}")


@cli.command()
def auth():
    """Check Copilot authentication status."""
    import asyncio
    from grader import check_copilot_auth
    
    console.print("[blue]🔐[/blue] Checking Copilot SDK status...")
    console.print()
    
    result = asyncio.run(check_copilot_auth())
    
    # CLI availability
    if result.get("cli_available"):
        console.print("[green]✓[/green] Copilot CLI found")
    else:
        console.print("[red]✗[/red] Copilot CLI not found")
    
    # Authentication status
    if result["authenticated"]:
        console.print(f"[green]✓[/green] Authenticated as [cyan]{result['login']}[/cyan]")
        console.print()
        console.print("[dim]You can run the daemon with --no-mock to use Copilot grading[/dim]")
    else:
        console.print(f"[yellow]ℹ[/yellow] {result['message']}")
        console.print()
        console.print("[yellow]Current options:[/yellow]")
        console.print("  1. Use mock grading (default): [cyan]python daemon.py run[/cyan]")
        console.print("  2. Install Copilot CLI:")
        console.print("     [dim]npm install -g @github/copilot[/dim]")
        console.print("     [dim]copilot auth login[/dim]")
        console.print("     [dim]python daemon.py run --no-mock[/dim]")


if __name__ == "__main__":
    cli()
