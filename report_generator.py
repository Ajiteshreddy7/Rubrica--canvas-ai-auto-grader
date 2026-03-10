"""
HTML Report Generator for Rubrica Analytics

This module generates a self-contained HTML report with embedded Chart.js visualizations
from the analytics data produced by analytics.generate_full_report().
"""

import json
from datetime import datetime
from typing import Dict, Any


def generate_html_report(report_data: Dict[str, Any], output_path: str = "analytics_report.html") -> str:
    """
    Generate a self-contained HTML report with embedded Chart.js charts.

    Args:
        report_data: Dictionary containing analytics data from analytics.generate_full_report()
        output_path: Path where the HTML file should be saved (default: "analytics_report.html")

    Returns:
        str: Path to the generated HTML file
    """

    # Extract data for easier access
    overall = report_data.get("overall", {})
    per_assignment = report_data.get("per_assignment", [])
    per_student = report_data.get("per_student", [])
    feedback_patterns = report_data.get("feedback_patterns", {})
    generated_at = report_data.get("generated_at", datetime.now().isoformat())

    # Build the HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rubrica Analytics Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .header p {{
            opacity: 0.9;
            font-size: 0.95rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .card-title {{
            font-size: 0.875rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}

        .card-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }}

        .section {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }}

        .chart-container {{
            position: relative;
            margin: 1.5rem 0;
            padding: 1rem;
        }}

        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}

        .chart-wrapper.tall {{
            height: 600px;
        }}

        .assignment-chart {{
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid #eee;
        }}

        .assignment-chart:last-child {{
            border-bottom: none;
        }}

        .assignment-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #444;
            margin-bottom: 1rem;
        }}

        .assignment-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
            padding: 1rem;
            background: #f9f9f9;
            border-radius: 6px;
        }}

        .stat-item {{
            text-align: center;
        }}

        .stat-label {{
            font-size: 0.75rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-value {{
            font-size: 1.25rem;
            font-weight: bold;
            color: #333;
            margin-top: 0.25rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }}

        th:hover {{
            background: #5568d3;
        }}

        td {{
            padding: 0.875rem 1rem;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .performance-high {{
            background-color: #d4edda;
            color: #155724;
        }}

        .performance-medium {{
            background-color: #fff3cd;
            color: #856404;
        }}

        .performance-low {{
            background-color: #f8d7da;
            color: #721c24;
        }}

        .feedback-list {{
            list-style: none;
            padding: 0;
        }}

        .feedback-item {{
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #f9f9f9;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .feedback-text {{
            flex: 1;
        }}

        .feedback-count {{
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: bold;
        }}

        .subsection {{
            margin-bottom: 2rem;
        }}

        .subsection-title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #555;
            margin-bottom: 1rem;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }}

        .no-data {{
            text-align: center;
            padding: 2rem;
            color: #999;
            font-style: italic;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            .header {{
                padding: 1.5rem 1rem;
            }}

            .header h1 {{
                font-size: 1.5rem;
            }}

            .section {{
                padding: 1.5rem 1rem;
            }}

            .chart-wrapper {{
                height: 300px;
            }}

            .grid-2 {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 0.875rem;
            }}

            th, td {{
                padding: 0.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Rubrica Analytics Report</h1>
        <p>Generated on {_format_datetime(generated_at)}</p>
    </div>

    <div class="container">
        <!-- Overall Summary Cards -->
        <div class="summary-cards">
            <div class="card">
                <div class="card-title">Total Graded</div>
                <div class="card-value">{overall.get('total_graded', 0)}</div>
            </div>
            <div class="card">
                <div class="card-title">Students</div>
                <div class="card-value">{overall.get('total_students', 0)}</div>
            </div>
            <div class="card">
                <div class="card-title">Assignments</div>
                <div class="card-value">{overall.get('total_assignments', 0)}</div>
            </div>
            <div class="card">
                <div class="card-title">Average Score</div>
                <div class="card-value">{overall.get('overall_avg_percentage', 0):.1f}%</div>
            </div>
            <div class="card">
                <div class="card-title">Pass Rate</div>
                <div class="card-value">{overall.get('overall_pass_rate', 0):.1f}%</div>
            </div>
        </div>

        <!-- Submission Type Breakdown -->
        {_generate_submission_type_section(overall.get('type_breakdown', {}))}

        <!-- Assignment Comparison -->
        {_generate_assignment_comparison_section(per_assignment)}

        <!-- Per-Assignment Score Distributions -->
        {_generate_assignment_distributions_section(per_assignment)}

        <!-- Student Performance Table -->
        {_generate_student_table_section(per_student)}

        <!-- Feedback Patterns -->
        {_generate_feedback_section(feedback_patterns)}
    </div>

    <script>
        // Data embedded from Python
        const reportData = {json.dumps(report_data, indent=2)};

        // Chart.js default configuration
        Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
        Chart.defaults.color = '#666';

        // Color palette
        const colors = {{
            primary: '#667eea',
            secondary: '#764ba2',
            success: '#28a745',
            warning: '#ffc107',
            danger: '#dc3545',
            info: '#17a2b8',
            palette: [
                '#667eea', '#764ba2', '#f093fb', '#4facfe',
                '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                '#a8edea', '#fed6e3', '#c3cfe2', '#f8b500'
            ]
        }};

        {_generate_submission_type_chart_js(overall.get('type_breakdown', {}))}

        {_generate_assignment_comparison_chart_js(per_assignment)}

        {_generate_assignment_distribution_charts_js(per_assignment)}

        {_generate_table_sorting_js()}
    </script>
</body>
</html>"""

    # Write the HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def _format_datetime(iso_string: str) -> str:
    """Format ISO datetime string to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        return iso_string


def _generate_submission_type_section(type_breakdown: Dict[str, int]) -> str:
    """Generate HTML for submission type breakdown section."""
    if not type_breakdown:
        return '<div class="section"><div class="no-data">No submission type data available</div></div>'

    return f"""
        <div class="section">
            <h2 class="section-title">Submission Type Breakdown</h2>
            <div class="chart-container">
                <div class="chart-wrapper">
                    <canvas id="submissionTypeChart"></canvas>
                </div>
            </div>
        </div>
    """


def _generate_assignment_comparison_section(per_assignment: list) -> str:
    """Generate HTML for assignment comparison section."""
    if not per_assignment:
        return '<div class="section"><div class="no-data">No assignment data available</div></div>'

    return """
        <div class="section">
            <h2 class="section-title">Assignment Performance Comparison</h2>
            <div class="chart-container">
                <div class="chart-wrapper tall">
                    <canvas id="assignmentComparisonChart"></canvas>
                </div>
            </div>
        </div>
    """


def _generate_assignment_distributions_section(per_assignment: list) -> str:
    """Generate HTML for per-assignment score distribution charts."""
    if not per_assignment:
        return '<div class="section"><div class="no-data">No assignment data available</div></div>'

    html = '<div class="section"><h2 class="section-title">Score Distributions by Assignment</h2>'

    for idx, assignment in enumerate(per_assignment):
        assignment_id = assignment.get('assignment_id', f'assignment_{idx}')
        assignment_title = assignment.get('assignment_title', 'Unknown Assignment')
        count = assignment.get('count', 0)
        avg_score = assignment.get('avg_score', 0)
        median_score = assignment.get('median_score', 0)
        min_score = assignment.get('min_score', 0)
        max_score = assignment.get('max_score', 0)
        std_dev = assignment.get('std_dev', 0)
        max_points = assignment.get('max_points', 0)
        avg_percentage = assignment.get('avg_percentage', 0)
        pass_rate = assignment.get('pass_rate', 0)

        html += f"""
        <div class="assignment-chart">
            <h3 class="assignment-title">{assignment_title}</h3>
            <div class="assignment-stats">
                <div class="stat-item">
                    <div class="stat-label">Submissions</div>
                    <div class="stat-value">{count}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Avg Score</div>
                    <div class="stat-value">{avg_score:.1f}/{max_points:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Avg %</div>
                    <div class="stat-value">{avg_percentage:.1f}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Median</div>
                    <div class="stat-value">{median_score:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Range</div>
                    <div class="stat-value">{min_score:.1f}-{max_score:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Std Dev</div>
                    <div class="stat-value">{std_dev:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Pass Rate</div>
                    <div class="stat-value">{pass_rate:.1f}%</div>
                </div>
            </div>
            <div class="chart-container">
                <div class="chart-wrapper">
                    <canvas id="distChart_{idx}"></canvas>
                </div>
            </div>
        </div>
        """

    html += '</div>'
    return html


def _generate_student_table_section(per_student: list) -> str:
    """Generate HTML for student performance table."""
    if not per_student:
        return '<div class="section"><div class="no-data">No student data available</div></div>'

    html = """
        <div class="section">
            <h2 class="section-title">Student Performance</h2>
            <table id="studentTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Student</th>
                        <th onclick="sortTable(1)">Assignments</th>
                        <th onclick="sortTable(2)">Average %</th>
                        <th onclick="sortTable(3)">Total Score</th>
                        <th onclick="sortTable(4)">Max Points</th>
                    </tr>
                </thead>
                <tbody>
    """

    for student in per_student:
        student_name = student.get('student', 'Unknown')
        assignments_graded = student.get('assignments_graded', 0)
        avg_percentage = student.get('avg_percentage', 0)
        total_score = student.get('total_score', 0)
        total_max_points = student.get('total_max_points', 0)

        # Determine performance class
        if avg_percentage >= 80:
            perf_class = 'performance-high'
        elif avg_percentage >= 60:
            perf_class = 'performance-medium'
        else:
            perf_class = 'performance-low'

        html += f"""
                    <tr>
                        <td>{student_name}</td>
                        <td>{assignments_graded}</td>
                        <td class="{perf_class}">{avg_percentage:.1f}%</td>
                        <td>{total_score:.1f}</td>
                        <td>{total_max_points:.1f}</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>
    """
    return html


def _generate_feedback_section(feedback_patterns: Dict[str, Any]) -> str:
    """Generate HTML for feedback patterns section."""
    if not feedback_patterns:
        return '<div class="section"><div class="no-data">No feedback data available</div></div>'

    common_strengths = feedback_patterns.get('common_strengths', [])
    common_improvements = feedback_patterns.get('common_improvements', [])
    assignments_with_issues = feedback_patterns.get('assignments_with_issues', {})

    html = '<div class="section"><h2 class="section-title">Feedback Patterns</h2><div class="grid-2">'

    # Common Strengths
    html += '<div class="subsection"><h3 class="subsection-title">Common Strengths</h3>'
    if common_strengths:
        html += '<ul class="feedback-list">'
        for pattern, count in common_strengths[:10]:  # Top 10
            html += f'<li class="feedback-item"><span class="feedback-text">{pattern}</span><span class="feedback-count">{count}</span></li>'
        html += '</ul>'
    else:
        html += '<div class="no-data">No strength patterns found</div>'
    html += '</div>'

    # Common Improvements
    html += '<div class="subsection"><h3 class="subsection-title">Common Areas for Improvement</h3>'
    if common_improvements:
        html += '<ul class="feedback-list">'
        for pattern, count in common_improvements[:10]:  # Top 10
            html += f'<li class="feedback-item"><span class="feedback-text">{pattern}</span><span class="feedback-count">{count}</span></li>'
        html += '</ul>'
    else:
        html += '<div class="no-data">No improvement patterns found</div>'
    html += '</div>'

    html += '</div>'

    # Assignments with Issues
    if assignments_with_issues:
        html += '<div class="subsection"><h3 class="subsection-title">Assignments with Common Issues</h3>'
        for assignment_title, issues in list(assignments_with_issues.items())[:5]:  # Top 5 assignments
            html += f'<div style="margin-bottom: 1.5rem;"><h4 style="color: #555; margin-bottom: 0.5rem;">{assignment_title}</h4>'
            html += '<ul class="feedback-list">'
            for issue, count in issues[:5]:  # Top 5 issues per assignment
                html += f'<li class="feedback-item"><span class="feedback-text">{issue}</span><span class="feedback-count">{count}</span></li>'
            html += '</ul></div>'
        html += '</div>'

    html += '</div>'
    return html


def _generate_submission_type_chart_js(type_breakdown: Dict[str, int]) -> str:
    """Generate JavaScript code for submission type chart."""
    if not type_breakdown:
        return ''

    labels = list(type_breakdown.keys())
    data = list(type_breakdown.values())

    return f"""
        // Submission Type Pie Chart
        const submissionTypeCtx = document.getElementById('submissionTypeChart');
        if (submissionTypeCtx) {{
            new Chart(submissionTypeCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        data: {json.dumps(data)},
                        backgroundColor: colors.palette,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right',
                            labels: {{
                                padding: 15,
                                font: {{
                                    size: 12
                                }}
                            }}
                        }},
                        title: {{
                            display: false
                        }}
                    }}
                }}
            }});
        }}
    """


def _generate_assignment_comparison_chart_js(per_assignment: list) -> str:
    """Generate JavaScript code for assignment comparison chart."""
    if not per_assignment:
        return ''

    # Sort by average percentage for better visualization
    sorted_assignments = sorted(per_assignment, key=lambda x: x.get('avg_percentage', 0))

    labels = [a.get('assignment_title', 'Unknown') for a in sorted_assignments]
    avg_percentages = [a.get('avg_percentage', 0) for a in sorted_assignments]
    pass_rates = [a.get('pass_rate', 0) for a in sorted_assignments]

    return f"""
        // Assignment Comparison Chart
        const assignmentCompCtx = document.getElementById('assignmentComparisonChart');
        if (assignmentCompCtx) {{
            new Chart(assignmentCompCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [
                        {{
                            label: 'Average Score %',
                            data: {json.dumps(avg_percentages)},
                            backgroundColor: colors.primary,
                            borderColor: colors.primary,
                            borderWidth: 1
                        }},
                        {{
                            label: 'Pass Rate %',
                            data: {json.dumps(pass_rates)},
                            backgroundColor: colors.success,
                            borderColor: colors.success,
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            max: 100,
                            grid: {{
                                display: true
                            }},
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }},
                        y: {{
                            grid: {{
                                display: false
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.x.toFixed(1) + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
    """


def _generate_assignment_distribution_charts_js(per_assignment: list) -> str:
    """Generate JavaScript code for all assignment distribution charts."""
    if not per_assignment:
        return ''

    js_code = ""

    for idx, assignment in enumerate(per_assignment):
        score_distribution = assignment.get('score_distribution', [])
        if not score_distribution:
            continue

        labels = [d.get('range', '') for d in score_distribution]
        counts = [d.get('count', 0) for d in score_distribution]

        # Color code based on score range
        colors_list = []
        for label in labels:
            if label.startswith('0-') or label.startswith('10-') or label.startswith('20-') or label.startswith('30-') or label.startswith('40-') or label.startswith('50-'):
                colors_list.append('#dc3545')  # Red for failing grades
            elif label.startswith('60-') or label.startswith('70-'):
                colors_list.append('#ffc107')  # Yellow for passing but low
            else:
                colors_list.append('#28a745')  # Green for good grades

        js_code += f"""
        // Distribution Chart for Assignment {idx}
        const distCtx_{idx} = document.getElementById('distChart_{idx}');
        if (distCtx_{idx}) {{
            new Chart(distCtx_{idx}, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: 'Number of Students',
                        data: {json.dumps(counts)},
                        backgroundColor: {json.dumps(colors_list)},
                        borderColor: {json.dumps(colors_list)},
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }},
                            grid: {{
                                display: true
                            }}
                        }},
                        x: {{
                            grid: {{
                                display: false
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return 'Students: ' + context.parsed.y;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
        """

    return js_code


def _generate_table_sorting_js() -> str:
    """Generate JavaScript code for table sorting functionality."""
    return """
        // Table sorting functionality
        function sortTable(columnIndex) {
            const table = document.getElementById('studentTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            // Determine current sort direction
            const header = table.querySelectorAll('th')[columnIndex];
            const currentDirection = header.dataset.sortDirection || 'asc';
            const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';

            // Clear all sort indicators
            table.querySelectorAll('th').forEach(th => {
                th.dataset.sortDirection = '';
            });
            header.dataset.sortDirection = newDirection;

            // Sort rows
            rows.sort((a, b) => {
                let aValue = a.cells[columnIndex].textContent.trim();
                let bValue = b.cells[columnIndex].textContent.trim();

                // Try to parse as number
                const aNum = parseFloat(aValue.replace('%', ''));
                const bNum = parseFloat(bValue.replace('%', ''));

                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return newDirection === 'asc' ? aNum - bNum : bNum - aNum;
                }

                // String comparison
                return newDirection === 'asc'
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            });

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }
    """


if __name__ == "__main__":
    # Example usage
    print("report_generator.py - HTML Report Generator for Rubrica")
    print("This module is meant to be imported and used with analytics data.")
    print("\nUsage:")
    print("  from report_generator import generate_html_report")
    print("  from analytics import generate_full_report")
    print("  ")
    print("  report_data = generate_full_report('graded_results.jsonl')")
    print("  output_path = generate_html_report(report_data, 'my_report.html')")
    print("  print(f'Report generated: {output_path}')")
