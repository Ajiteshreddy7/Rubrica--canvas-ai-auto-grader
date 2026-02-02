#!/usr/bin/env python3
"""
Dependency Verification Script

Checks all dependencies for the grading agent and provides helpful error messages.
Run this before starting the daemon to ensure everything is configured correctly.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_python_version():
    """Check if Python version is 3.9+."""
    version = sys.version_info
    required = (3, 9)
    
    if version >= required:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (need 3.9+)"


def check_python_package(package_name):
    """Check if a Python package is installed."""
    try:
        __import__(package_name.replace("-", "_"))
        return True, "Installed"
    except ImportError:
        return False, "Missing"


def check_command(cmd):
    """Check if a command is available in PATH."""
    path = shutil.which(cmd)
    if path:
        return True, f"Found at: {path}"
    else:
        return False, "Not found in PATH"


def check_copilot_cli():
    """Check if Copilot CLI is installed and get version."""
    if not shutil.which("copilot"):
        return False, "Not installed (npm install -g @github/copilot)"
    
    try:
        result = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        version = result.stdout.strip()
        return True, f"v{version}" if version else "Installed"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Found but not working"


def check_copilot_auth():
    """Check if user is authenticated with Copilot."""
    if not shutil.which("copilot"):
        return False, "CLI not installed"
    
    try:
        result = subprocess.run(
            ["copilot", "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        if result.returncode == 0 and "logged in" in result.stdout.lower():
            # Extract username if possible
            lines = result.stdout.split("\n")
            for line in lines:
                if "as" in line.lower() or "@" in line:
                    return True, line.strip()
            return True, "Authenticated"
        else:
            return False, "Not authenticated (run: copilot auth login)"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return False, f"Cannot check auth"


def check_file_exists(filepath):
    """Check if a required file exists."""
    path = Path(filepath)
    if path.exists():
        return True, f"Found ({path.stat().st_size} bytes)"
    else:
        return False, "Missing"


def check_config():
    """Check if config.json has required fields."""
    config_path = Path("config.json")
    if not config_path.exists():
        return False, "File missing"
    
    try:
        import json
        with open(config_path) as f:
            config = json.load(f)
        
        # Check required fields
        required = {
            "canvas": ["base_url", "course_id", "assignment_id"],
            "github": []
        }
        
        missing = []
        for section, fields in required.items():
            if section not in config:
                missing.append(section)
            else:
                for field in fields:
                    if field not in config[section]:
                        missing.append(f"{section}.{field}")
        
        if missing:
            return False, f"Missing: {', '.join(missing)}"
        
        # Check if API token is placeholder
        if "api_token" in config.get("canvas", {}):
            token = config["canvas"]["api_token"]
            if not token or "YOUR_" in token or token == "":
                return False, "Canvas API token not set"
        
        return True, "Configured"
    except json.JSONDecodeError:
        return False, "Invalid JSON"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    console.print(Panel(
        "[bold cyan]Grading Agent - Dependency Check[/bold cyan]\n\n"
        "Verifying all dependencies and configuration...",
        title="System Check",
        border_style="cyan"
    ))
    
    # Create results table
    table = Table(title="\n📋 Dependency Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", width=30)
    table.add_column("Status", width=15)
    table.add_column("Details", style="dim")
    
    checks = []
    
    # Python Version
    success, detail = check_python_version()
    status = "[green]✓ OK[/green]" if success else "[red]✗ FAIL[/red]"
    table.add_row("Python Version", status, detail)
    checks.append(("Python", success))
    
    # Python Packages
    packages = [
        ("click", "click"),
        ("rich", "rich"),
        ("requests", "requests"),
        ("pydantic", "pydantic"),
        ("GitHub Copilot SDK", "copilot"),
        ("PyPDF2", "PyPDF2")
    ]
    
    for display_name, import_name in packages:
        success, detail = check_python_package(import_name)
        status = "[green]✓ OK[/green]" if success else "[yellow]○ WARN[/yellow]"
        table.add_row(f"  {display_name}", status, detail)
        checks.append((display_name, success))
    
    # External Commands
    success, detail = check_command("node")
    status = "[green]✓ OK[/green]" if success else "[yellow]○ WARN[/yellow]"
    table.add_row("Node.js", status, detail)
    checks.append(("Node.js", success))
    
    success, detail = check_command("npm")
    status = "[green]✓ OK[/green]" if success else "[yellow]○ WARN[/yellow]"
    table.add_row("npm", status, detail)
    checks.append(("npm", success))
    
    # Copilot CLI
    success, detail = check_copilot_cli()
    status = "[green]✓ OK[/green]" if success else "[yellow]○ WARN[/yellow]"
    table.add_row("Copilot CLI", status, detail)
    checks.append(("Copilot CLI", success))
    
    # Copilot Auth
    success, detail = check_copilot_auth()
    status = "[green]✓ OK[/green]" if success else "[yellow]○ WARN[/yellow]"
    table.add_row("Copilot Auth", status, detail)
    checks.append(("Copilot Auth", success))
    
    # Configuration Files
    files = [
        ("config.json", "config.json"),
        ("status.json", "status.json"),
        ("rubric.md", "rubric.md"),
        ("prompts/system.md", "prompts/system.md"),
        ("prompts/grading.md", "prompts/grading.md"),
    ]
    
    for display_name, filepath in files:
        success, detail = check_file_exists(filepath)
        status = "[green]✓ OK[/green]" if success else "[red]✗ MISS[/red]"
        table.add_row(f"  {display_name}", status, detail)
        checks.append((display_name, success))
    
    # Config validation
    success, detail = check_config()
    status = "[green]✓ OK[/green]" if success else "[red]✗ FAIL[/red]"
    table.add_row("Canvas Configuration", status, detail)
    checks.append(("Canvas Config", success))
    
    console.print(table)
    
    # Summary
    console.print("\n" + "="*60 + "\n")
    
    critical_deps = ["Python", "click", "rich", "requests", "Canvas Config"]
    critical_missing = [name for name, success in checks if name in critical_deps and not success]
    
    optional_deps = ["Copilot CLI", "Copilot Auth", "Node.js", "npm"]
    optional_missing = [name for name, success in checks if name in optional_deps and not success]
    
    if critical_missing:
        console.print(Panel(
            f"[bold red]✗ CRITICAL ISSUES FOUND[/bold red]\n\n"
            f"Missing critical dependencies:\n"
            + "\n".join(f"  • {dep}" for dep in critical_missing) +
            "\n\n[bold]Action Required:[/bold]\n"
            "1. Install missing Python packages: pip install -r requirements.txt\n"
            "2. Configure config.json with Canvas API credentials\n"
            "3. Run this check again",
            title="Status: Not Ready",
            border_style="red"
        ))
        return 1
    elif optional_missing:
        console.print(Panel(
            f"[bold yellow]⚠ OPTIONAL DEPENDENCIES MISSING[/bold yellow]\n\n"
            f"Missing optional dependencies:\n"
            + "\n".join(f"  • {dep}" for dep in optional_missing) +
            "\n\n[bold]Available Modes:[/bold]\n"
            "[green]✓[/green] Mock Mode: python daemon.py run (works now)\n"
            "[yellow]○[/yellow] Copilot Mode: python daemon.py run --no-mock (needs setup)\n\n"
            "[bold]To enable Copilot Mode:[/bold]\n"
            "1. Run: python setup_copilot.py\n"
            "2. Follow the interactive setup",
            title="Status: Partially Ready",
            border_style="yellow"
        ))
        return 0
    else:
        console.print(Panel(
            "[bold green]✓ ALL DEPENDENCIES SATISFIED[/bold green]\n\n"
            "[bold]Ready to start grading![/bold]\n\n"
            "Available commands:\n"
            "  • python daemon.py run          [dim](mock mode)[/dim]\n"
            "  • python daemon.py run --no-mock [dim](Copilot AI)[/dim]\n"
            "  • python daemon.py status        [dim](check submissions)[/dim]\n"
            "  • python daemon.py auth          [dim](verify Copilot auth)[/dim]",
            title="Status: Ready ✨",
            border_style="green"
        ))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Check cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {str(e)}")
        sys.exit(1)
