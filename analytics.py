"""
Analytics Engine

Reads completed submissions from queue.json and grading.md files
to compute score distributions, averages, and per-assignment stats.
"""

import json
import re
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime

from submission_queue import _load_queue


def _parse_grading_frontmatter(grading_path: Path) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from a grading.md file."""
    if not grading_path.exists():
        return None

    text = grading_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None

    # Extract frontmatter between --- markers
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    # Parse score as float
    if "score" in frontmatter:
        try:
            frontmatter["score"] = float(frontmatter["score"])
        except ValueError:
            frontmatter["score"] = 0.0

    # Store the feedback body for pattern analysis
    frontmatter["_feedback_body"] = parts[2].strip()

    return frontmatter


def _parse_feedback_sections(feedback_body: str) -> Dict[str, str]:
    """
    Extract named sections from grading feedback markdown.

    Returns dict with section names as keys (e.g. 'Strengths', 'Summary').
    """
    sections = {}
    current_section = None
    current_lines = []

    for line in feedback_body.splitlines():
        # Match ## headings (with or without emoji)
        heading_match = re.match(r"^##\s+(?:[\U0001f300-\U0001faff\u2600-\u27bf]\s*)?(.+)", line)
        if heading_match:
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = heading_match.group(1).strip()
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def collect_grading_data() -> List[Dict[str, Any]]:
    """
    Collect all grading data from two sources:
    1. Completed items in queue.json (has score, student, assignment)
    2. grading.md files on disk (has feedback text)

    Returns list of dicts with keys:
        student, assignment_id, assignment_title, score, max_points,
        submission_type, graded_at, feedback_sections
    """
    records = []

    # Source 1: queue.json completed items
    try:
        queue = _load_queue()
    except Exception:
        queue = {"pending": [], "processing": None, "completed": [], "failed": []}
    completed = queue.get("completed", [])

    # Build lookup from queue for fast matching
    queue_lookup = {}
    for item in completed:
        key = f"{item.get('assignment_id')}_{item.get('student_login')}"
        queue_lookup[key] = item

    # Source 2: Walk all grading.md files on disk
    assignments_dir = Path("assignments")
    if not assignments_dir.exists():
        return records

    for grading_file in assignments_dir.rglob("grading.md"):
        fm = _parse_grading_frontmatter(grading_file)
        if not fm or "score" not in fm:
            continue

        # Try to get max_points from assignment.json
        assignment_folder = grading_file.parent.parent.parent
        max_points = 1.0
        assignment_json = assignment_folder / "assignment.json"
        if assignment_json.exists():
            try:
                with open(assignment_json, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    max_points = float(meta.get("points_possible", 1))
            except (json.JSONDecodeError, ValueError):
                pass

        feedback_sections = _parse_feedback_sections(fm.get("_feedback_body", ""))

        record = {
            "student": fm.get("student", "Unknown"),
            "assignment_id": fm.get("assignment_id", ""),
            "assignment_title": fm.get("assignment_title", ""),
            "score": fm["score"],
            "max_points": max_points,
            "percentage": (fm["score"] / max_points * 100) if max_points > 0 else 0,
            "submission_type": fm.get("submission_type", "unknown"),
            "graded_at": fm.get("graded_at", ""),
            "feedback_sections": feedback_sections,
            "grading_file": str(grading_file),
        }
        records.append(record)

    return records


def per_assignment_stats(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute statistics per assignment.

    Returns list of dicts with:
        assignment_id, assignment_title, count, avg_score, median_score,
        min_score, max_score, std_dev, max_points, avg_percentage,
        pass_count, fail_count, pass_rate, score_distribution
    """
    grouped = defaultdict(list)
    for r in records:
        grouped[r["assignment_id"]].append(r)

    results = []
    for assignment_id, items in sorted(grouped.items()):
        scores = [i["score"] for i in items]
        percentages = [i["percentage"] for i in items]
        max_points = items[0]["max_points"]
        title = items[0]["assignment_title"]

        # Pass/fail: >= 60% is passing
        pass_count = sum(1 for p in percentages if p >= 60)
        fail_count = len(percentages) - pass_count

        # Score distribution: buckets of 10%
        distribution = defaultdict(int)
        for p in percentages:
            bucket = min(int(p // 10) * 10, 100)
            distribution[bucket] += 1
        # Fill missing buckets
        dist_list = []
        for b in range(0, 110, 10):
            dist_list.append({"range": f"{b}-{b+9}%", "count": distribution.get(b, 0)})

        results.append({
            "assignment_id": assignment_id,
            "assignment_title": title,
            "count": len(scores),
            "avg_score": round(statistics.mean(scores), 2),
            "median_score": round(statistics.median(scores), 2),
            "min_score": min(scores),
            "max_score": max(scores),
            "std_dev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            "max_points": max_points,
            "avg_percentage": round(statistics.mean(percentages), 1),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": round(pass_count / len(scores) * 100, 1) if scores else 0,
            "score_distribution": dist_list,
        })

    return results


def per_student_stats(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute statistics per student across all assignments.

    Returns list of dicts with:
        student, assignments_graded, avg_percentage, total_score,
        total_max_points, scores_by_assignment
    """
    grouped = defaultdict(list)
    for r in records:
        grouped[r["student"]].append(r)

    results = []
    for student, items in sorted(grouped.items()):
        total_score = sum(i["score"] for i in items)
        total_max = sum(i["max_points"] for i in items)
        percentages = [i["percentage"] for i in items]

        scores_by_assignment = [
            {
                "assignment_title": i["assignment_title"],
                "score": i["score"],
                "max_points": i["max_points"],
                "percentage": i["percentage"],
            }
            for i in sorted(items, key=lambda x: x.get("graded_at", ""))
        ]

        results.append({
            "student": student,
            "assignments_graded": len(items),
            "avg_percentage": round(statistics.mean(percentages), 1),
            "total_score": round(total_score, 2),
            "total_max_points": round(total_max, 2),
            "scores_by_assignment": scores_by_assignment,
        })

    return results


def submission_type_breakdown(records: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count submissions by type (github, pdf, text, etc.)."""
    counts = defaultdict(int)
    for r in records:
        counts[r["submission_type"]] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def overall_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute overall course-level statistics.

    Returns dict with:
        total_graded, total_students, total_assignments,
        overall_avg_percentage, overall_pass_rate, type_breakdown
    """
    if not records:
        return {
            "total_graded": 0,
            "total_students": 0,
            "total_assignments": 0,
            "overall_avg_percentage": 0,
            "overall_pass_rate": 0,
            "type_breakdown": {},
        }

    students = set(r["student"] for r in records)
    assignments = set(r["assignment_id"] for r in records)
    percentages = [r["percentage"] for r in records]
    pass_count = sum(1 for p in percentages if p >= 60)

    return {
        "total_graded": len(records),
        "total_students": len(students),
        "total_assignments": len(assignments),
        "overall_avg_percentage": round(statistics.mean(percentages), 1),
        "overall_pass_rate": round(pass_count / len(records) * 100, 1),
        "type_breakdown": submission_type_breakdown(records),
    }


def extract_feedback_patterns(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze grading feedback to find common themes.

    Returns dict with:
        common_strengths: list of (pattern, count) tuples
        common_improvements: list of (pattern, count) tuples
        assignments_with_issues: dict of assignment -> list of common issues
    """
    strengths = defaultdict(int)
    improvements = defaultdict(int)
    issues_by_assignment = defaultdict(lambda: defaultdict(int))

    for r in records:
        sections = r.get("feedback_sections", {})
        assignment_title = r.get("assignment_title", "")

        # Extract bullet points from Strengths section
        for section_name, text in sections.items():
            lower_name = section_name.lower()
            is_strength = "strength" in lower_name
            is_improvement = any(
                kw in lower_name for kw in
                ["improvement", "issue", "weakness", "suggestion", "feedback"]
            )

            for line in text.splitlines():
                line = line.strip()
                # Match bullet points: -, *, or numbered
                bullet_match = re.match(r"^[-*]\s+(.+)$", line)
                if not bullet_match:
                    bullet_match = re.match(r"^\d+[.)]\s+(.+)$", line)
                if not bullet_match:
                    continue

                point = bullet_match.group(1).strip()
                if len(point) < 5:
                    continue

                if is_strength:
                    strengths[point] += 1
                elif is_improvement:
                    improvements[point] += 1
                    issues_by_assignment[assignment_title][point] += 1

    # Sort by frequency
    top_strengths = sorted(strengths.items(), key=lambda x: -x[1])[:15]
    top_improvements = sorted(improvements.items(), key=lambda x: -x[1])[:15]

    # Top issues per assignment
    assignment_issues = {}
    for assignment, issues in issues_by_assignment.items():
        top = sorted(issues.items(), key=lambda x: -x[1])[:5]
        if top:
            assignment_issues[assignment] = top

    return {
        "common_strengths": top_strengths,
        "common_improvements": top_improvements,
        "assignments_with_issues": assignment_issues,
    }


def generate_full_report() -> Dict[str, Any]:
    """
    Generate a complete analytics report.

    Returns dict with all analytics data ready for rendering.
    """
    records = collect_grading_data()

    return {
        "generated_at": datetime.now().isoformat(),
        "overall": overall_stats(records),
        "per_assignment": per_assignment_stats(records),
        "per_student": per_student_stats(records),
        "feedback_patterns": extract_feedback_patterns(records),
        "record_count": len(records),
    }
