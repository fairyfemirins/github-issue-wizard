#!/usr/bin/env python3
"""
GitHub Issue Wizard
Autonomously triage GitHub issues with a human-in-the-loop interactive CLI.

Usage:
    python github_issue_wizard.py --repo <owner/repo> --token <github_token>
"""

import argparse
import os
import sys
from github import Github
import questionary
from rich.console import Console
from rich.table import Table

console = Console()

def parse_args():
    parser = argparse.ArgumentParser(description="Autonomously triage GitHub issues.")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., 'owner/repo')")
    parser.add_argument("--token", required=True, help="GitHub personal access token")
    parser.add_argument("--dry-run", action="store_true", help="Simulate triage without applying changes")
    return parser.parse_args()

def analyze_issue(issue):
    """Analyze issue title/body and suggest labels/milestone."""
    title = issue.title.lower()
    body = issue.body.lower() if issue.body else ""
    text = f"{title} {body}"
    
    # Rule-based suggestions
    suggestions = {"labels": [], "milestone": None}
    
    if "bug" in text or "error" in text or "crash" in text:
        suggestions["labels"].append("bug")
    if "feature" in text or "enhancement" in text or "request" in text:
        suggestions["labels"].append("enhancement")
    if "question" in text or "help" in text:
        suggestions["labels"].append("question")
    if "documentation" in text or "docs" in text:
        suggestions["labels"].append("documentation")
    
    # Suggest milestone if mentioned
    if "v1.0" in text or "1.0" in text:
        suggestions["milestone"] = "v1.0"
    elif "v2.0" in text or "2.0" in text:
        suggestions["milestone"] = "v2.0"
    
    return suggestions

def confirm_suggestions(issue, suggestions):
    """Interactive wizard for human-in-the-loop confirmation."""
    console.print(f"\n[bold]Issue #{issue.number}: {issue.title}[/bold]")
    console.print(f"URL: {issue.html_url}")
    
    # Display suggestions
    table = Table(title="Suggested Triage")
    table.add_column("Type", style="cyan")
    table.add_column("Suggestion", style="green")
    
    for label in suggestions["labels"]:
        table.add_row("Label", label)
    if suggestions["milestone"]:
        table.add_row("Milestone", suggestions["milestone"])
    console.print(table)
    
    # Confirm labels
    confirmed_labels = []
    for label in suggestions["labels"]:
        confirm = questionary.confirm(f"Apply label '{label}'?").ask()
        if confirm:
            confirmed_labels.append(label)
    
    # Confirm milestone
    confirmed_milestone = None
    if suggestions["milestone"]:
        confirm = questionary.confirm(f"Set milestone to '{suggestions['milestone']}'?").ask()
        if confirm:
            confirmed_milestone = suggestions["milestone"]
    
    return {"labels": confirmed_labels, "milestone": confirmed_milestone}

def apply_triage(issue, triage, dry_run=False):
    """Apply confirmed labels/milestone to the issue."""
    if dry_run:
        for label in triage["labels"]:
            console.print(f"[blue][DRY RUN] Would apply label: {label}[/blue]")
        if triage["milestone"]:
            console.print(f"[blue][DRY RUN] Would set milestone: {triage['milestone']}[/blue]")
        return
    
    for label in triage["labels"]:
        try:
            issue.add_to_labels(label)
            console.print(f"[green]✓ Applied label: {label}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to apply label {label}: {e}[/red]")
    
    if triage["milestone"]:
        try:
            milestones = issue.repository.get_milestones()
            milestone = next((m for m in milestones if m.title == triage["milestone"]), None)
            if milestone:
                issue.edit(milestone=milestone)
                console.print(f"[green]✓ Set milestone: {triage['milestone']}[/green]")
            else:
                console.print(f"[yellow]! Milestone '{triage['milestone']}' not found[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Failed to set milestone: {e}[/red]")

def main():
    args = parse_args()
    
    # Authenticate with GitHub
    try:
        g = Github(args.token)
        repo = g.get_repo(args.repo)
    except Exception as e:
        console.print(f"[red]✗ GitHub authentication failed: {e}[/red]")
        sys.exit(1)
    
    # Fetch open issues
    issues = repo.get_issues(state="open")
    if not issues:
        console.print("[yellow]! No open issues found[/yellow]")
        return
    
    # Process each issue
    for issue in issues:
        if issue.pull_request:
            continue  # Skip PRs
        
        suggestions = analyze_issue(issue)
        triage = confirm_suggestions(issue, suggestions)
        apply_triage(issue, triage, dry_run=args.dry_run)

if __name__ == "__main__":
    main()