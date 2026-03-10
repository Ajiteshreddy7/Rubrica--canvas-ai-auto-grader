"""
Canvas AI Auto-Grader CLI

Usage:
    python cli.py run [--no-mock] [--poll-interval SECONDS] [--assignment NAME]
    python cli.py grade [--no-mock]
    python cli.py status [--detailed] [--failed] [--completed]
    python cli.py fix-queue
    python cli.py retry [--max-retries N]
    python cli.py export [--output FILE]
    python cli.py analytics [--html] [--json] [--output FILE] [--assignment NAME]
"""

import asyncio
import csv
import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def _numbered_menu(items, label_fn, header):
    """
    Display a numbered menu and return selected items.

    Args:
        items: List of objects to choose from.
        label_fn: Callable that returns the display string for each item.
        header: Header text to print above the menu.

    Returns:
        Selected items list, or None if user cancels.
    """
    console.print(f"\n{header}")
    for i, item in enumerate(items, 1):
        console.print(f"  [{i}] {label_fn(item)}")
    console.print("  [0] All")

    try:
        raw = input("\nSelect (comma-separated numbers, or 0 for all): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not raw:
        return None

    try:
        nums = [int(n.strip()) for n in raw.split(",")]
    except ValueError:
        console.print("[red]Invalid input.[/red]")
        return None

    if 0 in nums:
        return list(items)

    selected = []
    for n in nums:
        if 1 <= n <= len(items):
            selected.append(items[n - 1])
        else:
            console.print(f"[red]Invalid number: {n}[/red]")
            return None

    return selected


@click.group()
@click.version_option(version="1.2.0", prog_name="Canvas AI Auto-Grader")
def cli():
    """Canvas AI Auto-Grader - Autonomous grading with AI."""
    pass


@cli.command()
@click.option("--no-mock", is_flag=True, help="Use real AI grading (default is mock mode)")
@click.option("--poll-interval", type=int, default=None, help="Override poll interval in seconds")
@click.option("--assignment", "-a", multiple=True, help="Scope to assignment name(s) (repeatable)")
def run(no_mock, poll_interval, assignment):
    """Start the grading daemon."""
    import os
    from daemon_new import run_daemon

    if poll_interval is not None:
        os.environ["POLL_INTERVAL_OVERRIDE"] = str(poll_interval)

    mock = not no_mock
    assignment_names = list(assignment) if assignment else None
    asyncio.run(run_daemon(mock, assignment_names))


@cli.command()
@click.option("--no-mock", is_flag=True, help="Use real AI grading (default is mock mode)")
@click.option("--regrade", is_flag=True, help="Re-grade already graded submissions")
@click.option("--assignment", "-a", multiple=True, help="Assignment name substring (skip menu)")
@click.option("--all-students", is_flag=True, help="Grade all students (skip student menu)")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def grade(no_mock, regrade, assignment, all_students, yes):
    """Interactive one-shot grading: select assignments and students, then grade and exit.

    \b
    Examples:
      python cli.py grade                          # fully interactive
      python cli.py grade -a "Hands-on L6" --all-students --no-mock -y
    """
    from canvas import CanvasClient, parse_submission
    from daemon_new import run_grade

    mock = not no_mock
    non_interactive = bool(assignment)  # CLI flags provided -- skip menus

    console.print("[bold cyan]Canvas Auto-Grader - Interactive Grade[/bold cyan]")
    console.print(f"Mode: {'[yellow]Mock[/yellow]' if mock else '[green]AI[/green]'}\n")
    console.print("Fetching assignments from Canvas...")

    client = CanvasClient()
    all_assignments = client.get_all_assignments()  # No filter -- fetch everything

    if not all_assignments:
        console.print("[red]No assignments found.[/red]")
        return

    # Sort by name for a stable display order
    all_assignments.sort(key=lambda a: a.get("name", ""))

    # --- Select assignments ---
    if non_interactive:
        # Filter by CLI --assignment flags
        keywords = [k.lower() for k in assignment]
        selected_assignments = [
            a for a in all_assignments
            if any(kw in a.get("name", "").lower() for kw in keywords)
        ]
        if not selected_assignments:
            console.print(f"[red]No assignments match: {', '.join(assignment)}[/red]")
            return
        for a in selected_assignments:
            console.print(f"  Matched: {a['name']}")
    else:
        def assignment_label(a):
            pts = a.get("points_possible", "?")
            return f"{a['name']}  (ID: {a['id']}, {pts} pts)"

        selected_assignments = _numbered_menu(
            all_assignments, assignment_label, "Assignments:"
        )
        if not selected_assignments:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    console.print(f"\nSelected {len(selected_assignments)} assignment(s)")

    # --- Select students per assignment ---
    assignments_with_students = []

    for asn in selected_assignments:
        assignment_id = str(asn["id"])
        assignment_title = asn["name"]

        raw_submissions = client.get_submissions(assignment_id)

        # Parse and collect valid submissions
        students = []
        for raw_sub in raw_submissions:
            parsed = parse_submission(raw_sub)
            if parsed:
                login = (
                    raw_sub.get("user", {}).get("login_id")
                    or raw_sub.get("user", {}).get("name", "unknown")
                )
                name = raw_sub.get("user", {}).get("name", login)
                students.append({
                    "login": login,
                    "name": name,
                    "parsed": parsed,
                })

        if not students:
            console.print(
                f"\n[dim]No submissions for '{assignment_title}' -- skipping.[/dim]"
            )
            continue

        students.sort(key=lambda s: s["name"].lower())

        if non_interactive or all_students:
            selected_students = students
        else:
            def student_label(s):
                return f"{s['name']}  ({s['parsed']['type']})"

            selected_students = _numbered_menu(
                students,
                student_label,
                f"\nStudents for '{assignment_title}' ({len(students)} submissions):",
            )
            if selected_students is None:
                console.print("[yellow]Cancelled.[/yellow]")
                return

        console.print(f"  Selected {len(selected_students)} student(s) for {assignment_title}")

        assignments_with_students.append({
            "assignment": asn,
            "students": [
                (s["login"], s["parsed"]) for s in selected_students
            ],
        })

    if not assignments_with_students:
        console.print("[yellow]Nothing to grade.[/yellow]")
        return

    total = sum(len(a["students"]) for a in assignments_with_students)
    console.print(
        f"\nReady to grade {total} submission(s) "
        f"across {len(assignments_with_students)} assignment(s)."
    )

    if not yes:
        try:
            confirm = input("Proceed? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        if confirm != "y":
            console.print("[yellow]Aborted.[/yellow]")
            return

    asyncio.run(run_grade(mock, assignments_with_students, regrade=regrade))


@cli.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed information")
@click.option("--failed", "-f", is_flag=True, help="Show only failed submissions")
@click.option("--completed", "-c", is_flag=True, help="Show recently completed submissions")
def status(detailed, failed, completed):
    """Show queue status."""
    from submission_queue import get_status as get_queue_status

    queue_status = get_queue_status()

    # Summary panel
    status_text = (
        f"Pending:    [yellow]{queue_status['pending_count']}[/yellow]\n"
        f"Processing: [cyan]{1 if queue_status['processing'] else 0}[/cyan]\n"
        f"Completed:  [green]{queue_status['completed_count']}[/green]\n"
        f"Failed:     [red]{queue_status['failed_count']}[/red]"
    )
    console.print(Panel(status_text, title="Queue Status", border_style="blue"))

    if failed or detailed:
        if queue_status["failed_items"]:
            console.print(f"\n[red]Failed Submissions:[/red]")
            table = Table(show_header=True)
            table.add_column("Student", style="cyan")
            table.add_column("Assignment")
            table.add_column("Error", style="red")
            table.add_column("Retries", justify="center")

            for item in queue_status["failed_items"]:
                error = item.get("error", item.get("last_error", "Unknown"))
                retries = str(item.get("retry_count", 0))
                table.add_row(
                    item["student_login"],
                    item["assignment_title"],
                    error[:60],
                    retries
                )
            console.print(table)
        else:
            console.print("[green]No failed submissions.[/green]")

    if completed or detailed:
        from submission_queue import _load_queue
        queue = _load_queue()
        completed_items = queue.get("completed", [])
        if completed_items:
            console.print(f"\n[green]Recently Completed (last 10):[/green]")
            table = Table(show_header=True)
            table.add_column("Student", style="cyan")
            table.add_column("Assignment")
            table.add_column("Score", justify="center", style="green")
            table.add_column("Completed At")

            for item in completed_items[-10:]:
                table.add_row(
                    item["student_login"],
                    item["assignment_title"],
                    str(item.get("score", "N/A")),
                    item.get("completed_at", "N/A")[:19]
                )
            console.print(table)
        else:
            console.print("[dim]No completed submissions yet.[/dim]")

    if detailed:
        if queue_status["pending_items"]:
            console.print(f"\n[yellow]Pending Queue:[/yellow]")
            table = Table(show_header=True)
            table.add_column("Student", style="cyan")
            table.add_column("Assignment")
            table.add_column("Type")
            table.add_column("Queued At")

            for item in queue_status["pending_items"]:
                table.add_row(
                    item["student_login"],
                    item["assignment_title"],
                    item.get("submission_type", "unknown"),
                    item.get("queued_at", "N/A")[:19]
                )
            console.print(table)

        if queue_status["processing"]:
            item = queue_status["processing"]
            console.print(
                f"\n[cyan]Currently Processing:[/cyan] "
                f"{item['student_login']} - {item['assignment_title']}"
            )


@cli.command("fix-queue")
def fix_queue_cmd():
    """Fix stuck queue items (e.g., after a crash)."""
    from fix_queue import fix_queue
    fix_queue()


@cli.command()
@click.option("--max-retries", type=int, default=1, help="Maximum retry attempts (default: 1)")
def retry(max_retries):
    """Retry all eligible failed submissions."""
    from submission_queue import get_retryable_failed, retry_all_eligible

    retryable = get_retryable_failed(max_retries=max_retries)
    if not retryable:
        console.print("[green]No retryable submissions found.[/green]")
        return

    console.print(f"[yellow]Found {len(retryable)} retryable submission(s):[/yellow]")
    for item in retryable:
        error = item.get("error", item.get("last_error", "Unknown"))
        console.print(f"  - {item['student_login']}: {error[:60]}")

    retried = retry_all_eligible(max_retries=max_retries)
    console.print(f"\n[green]Moved {retried} item(s) back to pending queue.[/green]")
    console.print("[dim]Run 'python cli.py run' to process them.[/dim]")


@cli.command()
@click.option("--output", "-o", type=click.Path(), default="grades.csv", help="Output CSV file path")
def export(output):
    """Export all grades to CSV."""
    from submission_queue import _load_queue

    queue = _load_queue()
    completed_items = queue.get("completed", [])

    if not completed_items:
        console.print("[yellow]No completed submissions to export.[/yellow]")
        return

    output_path = Path(output)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Student",
            "Assignment",
            "Assignment ID",
            "Score",
            "Submission Type",
            "Completed At",
            "Grading File"
        ])

        for item in completed_items:
            writer.writerow([
                item.get("student_login", ""),
                item.get("assignment_title", ""),
                item.get("assignment_id", ""),
                item.get("score", ""),
                item.get("submission_type", ""),
                item.get("completed_at", ""),
                item.get("grading_file", "")
            ])

    console.print(f"[green]Exported {len(completed_items)} grades to {output_path}[/green]")


@cli.command()
@click.option("--html", "html_flag", is_flag=True, help="Generate HTML report with charts")
@click.option("--json-out", "json_flag", is_flag=True, help="Output raw JSON data")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--assignment", "-a", type=str, default=None, help="Filter by assignment name substring")
def analytics(html_flag, json_flag, output, assignment):
    """Show score analytics and generate reports."""
    from analytics import (
        collect_grading_data,
        per_assignment_stats,
        per_student_stats,
        overall_stats,
        generate_full_report,
    )

    records = collect_grading_data()

    if not records:
        console.print("[yellow]No grading data found. Run the daemon first to grade submissions.[/yellow]")
        return

    # Filter by assignment if specified
    if assignment:
        assignment_lower = assignment.lower()
        records = [r for r in records if assignment_lower in r["assignment_title"].lower()]
        if not records:
            console.print(f"[yellow]No records match assignment filter '{assignment}'[/yellow]")
            return
        console.print(f"[dim]Filtered to {len(records)} records matching '{assignment}'[/dim]\n")

    # JSON output mode
    if json_flag:
        report = generate_full_report()
        if assignment:
            # Re-filter the full report
            report["per_assignment"] = [
                a for a in report["per_assignment"]
                if assignment.lower() in a["assignment_title"].lower()
            ]
        json_str = json.dumps(report, indent=2, default=str)
        if output:
            Path(output).write_text(json_str, encoding="utf-8")
            console.print(f"[green]JSON report saved to {output}[/green]")
        else:
            click.echo(json_str)
        return

    # HTML report mode
    if html_flag:
        from report_generator import generate_html_report

        report = generate_full_report()
        out_path = output or "analytics_report.html"
        result_path = generate_html_report(report, out_path)
        console.print(f"[green]HTML report generated: {result_path}[/green]")
        return

    # Default: Rich terminal output
    ov = overall_stats(records)
    assignments = per_assignment_stats(records)
    students = per_student_stats(records)

    # Overall summary panel
    summary = (
        f"Total Graded:   [bold]{ov['total_graded']}[/bold]\n"
        f"Students:       [bold]{ov['total_students']}[/bold]\n"
        f"Assignments:    [bold]{ov['total_assignments']}[/bold]\n"
        f"Average Score:  [bold]{ov['overall_avg_percentage']}%[/bold]\n"
        f"Pass Rate:      [bold]{ov['overall_pass_rate']}%[/bold]"
    )
    console.print(Panel(summary, title="Analytics Overview", border_style="blue"))

    # Submission type breakdown
    if ov["type_breakdown"]:
        type_parts = [f"{t}: [bold]{c}[/bold]" for t, c in ov["type_breakdown"].items()]
        console.print(f"\n[cyan]Submission Types:[/cyan] {' | '.join(type_parts)}")

    # Per-assignment table
    if assignments:
        console.print(f"\n[cyan]Per-Assignment Statistics:[/cyan]")
        table = Table(show_header=True)
        table.add_column("Assignment", max_width=40)
        table.add_column("N", justify="center")
        table.add_column("Avg Score", justify="center")
        table.add_column("Avg %", justify="center")
        table.add_column("Median", justify="center")
        table.add_column("Std Dev", justify="center")
        table.add_column("Pass Rate", justify="center")

        for a in assignments:
            pass_style = "green" if a["pass_rate"] >= 80 else ("yellow" if a["pass_rate"] >= 60 else "red")
            table.add_row(
                a["assignment_title"][:40],
                str(a["count"]),
                f"{a['avg_score']}/{a['max_points']}",
                f"{a['avg_percentage']}%",
                str(a["median_score"]),
                str(a["std_dev"]),
                f"[{pass_style}]{a['pass_rate']}%[/{pass_style}]",
            )
        console.print(table)

    # Top and bottom students
    if students and len(students) > 1:
        sorted_students = sorted(students, key=lambda s: -s["avg_percentage"])
        top_n = min(5, len(sorted_students))

        console.print(f"\n[green]Top {top_n} Students:[/green]")
        table = Table(show_header=True)
        table.add_column("Student", style="cyan")
        table.add_column("Assignments", justify="center")
        table.add_column("Avg %", justify="center", style="green")

        for s in sorted_students[:top_n]:
            table.add_row(s["student"], str(s["assignments_graded"]), f"{s['avg_percentage']}%")
        console.print(table)

        bottom = [s for s in sorted_students if s["avg_percentage"] < 60]
        if bottom:
            console.print(f"\n[red]Students Below 60%:[/red]")
            table = Table(show_header=True)
            table.add_column("Student", style="cyan")
            table.add_column("Assignments", justify="center")
            table.add_column("Avg %", justify="center", style="red")

            for s in bottom[:5]:
                table.add_row(s["student"], str(s["assignments_graded"]), f"{s['avg_percentage']}%")
            console.print(table)

    console.print(f"\n[dim]Use --html to generate a detailed HTML report with charts.[/dim]")


if __name__ == "__main__":
    cli()
