#!/usr/bin/env python3
"""
Copilot CLI Setup Script

Automates the installation and authentication of GitHub Copilot CLI for the grading agent.
This script handles the npm installation of @github/copilot and guides through authentication.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()


def check_command(cmd: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(cmd) is not None


def run_command(cmd: list, check=True, capture=False):
    """Run a shell command with error handling."""
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check)
            return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running command:[/red] {' '.join(cmd)}")
        if capture and e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        return None


def check_prerequisites():
    """Check if Node.js and npm are installed."""
    console.print("\n[bold cyan]🔍 Checking Prerequisites[/bold cyan]\n")
    
    has_node = check_command("node")
    has_npm = check_command("npm")
    
    if has_node:
        node_version = run_command(["node", "--version"], capture=True)
        console.print(f"[green]✓[/green] Node.js: {node_version}")
    else:
        console.print("[red]✗[/red] Node.js: Not found")
    
    if has_npm:
        npm_version = run_command(["npm", "--version"], capture=True)
        console.print(f"[green]✓[/green] npm: {npm_version}")
    else:
        console.print("[red]✗[/red] npm: Not found")
    
    if not (has_node and has_npm):
        console.print("\n[yellow]⚠ Node.js and npm are required to install Copilot CLI[/yellow]")
        console.print("\n[bold]Installation Instructions:[/bold]")
        console.print("1. Download from: https://nodejs.org/")
        console.print("2. Install Node.js LTS (includes npm)")
        console.print("3. Restart your terminal and run this script again")
        return False
    
    return True


def check_copilot_cli():
    """Check if Copilot CLI is already installed."""
    console.print("\n[bold cyan]🔍 Checking Copilot CLI[/bold cyan]\n")
    
    # Check if copilot command is available
    has_copilot = check_command("copilot")
    
    if has_copilot:
        version = run_command(["copilot", "--version"], capture=True)
        console.print(f"[green]✓[/green] Copilot CLI found: {version or 'installed'}")
        return True
    
    # Check if installed via npm global
    npm_list = run_command(["npm", "list", "-g", "@github/copilot", "--depth=0"], 
                          check=False, capture=True)
    if npm_list and "@github/copilot" in npm_list:
        console.print(f"[green]✓[/green] Copilot CLI installed via npm")
        return True
    
    console.print("[yellow]○[/yellow] Copilot CLI not found")
    return False


def install_copilot_cli():
    """Install Copilot CLI via npm."""
    console.print("\n[bold cyan]📦 Installing Copilot CLI[/bold cyan]\n")
    
    console.print("Installing @github/copilot globally...")
    console.print("[dim]This may take a few minutes...[/dim]\n")
    
    result = run_command(["npm", "install", "-g", "@github/copilot"])
    
    if result:
        console.print("\n[green]✓[/green] Copilot CLI installed successfully!")
        return True
    else:
        console.print("\n[red]✗[/red] Failed to install Copilot CLI")
        return False


def authenticate_copilot():
    """Guide user through Copilot CLI authentication."""
    console.print("\n[bold cyan]🔑 Authenticating with GitHub Copilot[/bold cyan]\n")
    
    console.print("[bold]You need to authenticate with GitHub to use Copilot.[/bold]")
    console.print("\nThis will:")
    console.print("  1. Open a browser for GitHub login")
    console.print("  2. Request Copilot access permissions")
    console.print("  3. Store credentials for the SDK to use")
    
    if not Confirm.ask("\nReady to authenticate?", default=True):
        console.print("[yellow]Skipping authentication. You can run 'copilot auth login' later.[/yellow]")
        return False
    
    console.print("\n[dim]Running: copilot auth login[/dim]\n")
    result = run_command(["copilot", "auth", "login"])
    
    if result:
        console.print("\n[green]✓[/green] Authentication successful!")
        return True
    else:
        console.print("\n[yellow]⚠[/yellow] Authentication may have failed. Try running 'copilot auth login' manually.")
        return False


def check_auth_status():
    """Check if user is already authenticated with Copilot."""
    console.print("\n[bold cyan]🔍 Checking Authentication Status[/bold cyan]\n")
    
    # Try to check auth status
    result = run_command(["copilot", "auth", "status"], check=False, capture=True)
    
    if result and "logged in" in result.lower():
        console.print("[green]✓[/green] Already authenticated with GitHub Copilot")
        return True
    else:
        console.print("[yellow]○[/yellow] Not authenticated")
        return False


def verify_installation():
    """Verify that everything is working."""
    console.print("\n[bold cyan]✓ Verifying Installation[/bold cyan]\n")
    
    # Check copilot command
    if not check_command("copilot"):
        console.print("[red]✗[/red] Copilot command not found in PATH")
        console.print("[yellow]Try restarting your terminal or adding npm global bin to PATH[/yellow]")
        return False
    
    # Check version
    version = run_command(["copilot", "--version"], capture=True)
    if version:
        console.print(f"[green]✓[/green] Copilot CLI version: {version}")
    
    # Check auth
    auth_result = run_command(["copilot", "auth", "status"], check=False, capture=True)
    if auth_result and "logged in" in auth_result.lower():
        console.print(f"[green]✓[/green] Authenticated and ready")
    else:
        console.print(f"[yellow]⚠[/yellow] Not authenticated (run 'copilot auth login')")
    
    return True


def show_next_steps():
    """Display next steps after setup."""
    console.print("\n" + "="*60 + "\n")
    console.print(Panel(
        "[bold green]✓ Setup Complete![/bold green]\n\n"
        "[bold]Next Steps:[/bold]\n\n"
        "1. Test the grading agent:\n"
        "   [cyan]conda activate grader[/cyan]\n"
        "   [cyan]python daemon.py auth[/cyan]\n\n"
        "2. Start grading (uses real Copilot):\n"
        "   [cyan]python daemon.py run --no-mock[/cyan]\n\n"
        "3. Or continue using mock mode (no Copilot needed):\n"
        "   [cyan]python daemon.py run[/cyan]\n\n"
        "[dim]The grading agent will now use GitHub Copilot for AI-powered grading.[/dim]",
        title="Setup Complete",
        border_style="green"
    ))


def main():
    """Main setup flow."""
    console.print(Panel(
        "[bold cyan]GitHub Copilot CLI Setup[/bold cyan]\n\n"
        "This script will install and configure the GitHub Copilot CLI\n"
        "for use with the grading agent.\n\n"
        "[dim]Make sure you have a GitHub Copilot subscription.[/dim]",
        title="Welcome",
        border_style="cyan"
    ))
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Check if already installed
    cli_installed = check_copilot_cli()
    
    # Install if needed
    if not cli_installed:
        if Confirm.ask("\nInstall Copilot CLI now?", default=True):
            if not install_copilot_cli():
                sys.exit(1)
        else:
            console.print("[yellow]Installation cancelled.[/yellow]")
            sys.exit(0)
    
    # Check authentication
    if not check_auth_status():
        if Confirm.ask("\nAuthenticate with GitHub now?", default=True):
            authenticate_copilot()
    
    # Verify everything works
    verify_installation()
    
    # Show next steps
    show_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {str(e)}")
        sys.exit(1)
