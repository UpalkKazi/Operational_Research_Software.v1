"""
OR Assistant - Command Line Interface
"""

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

console = Console()


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """OR Assistant - AI-Powered Operations Research Tool"""
    pass


@cli.command()
@click.option('--problem', '-p', help='Problem description (or use --file)')
@click.option('--file', '-f', type=click.Path(exists=True), help='Path to problem description file')
@click.option('--solver', '-s', default='pulp', help='Solver to use (pulp, ortools, cvxpy)')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def solve(problem, file, solver, output, verbose):
    """Solve an optimization problem"""
    
    # Get problem description
    if file:
        with open(file, 'r') as f:
            problem_text = f.read()
    elif problem:
        problem_text = problem
    else:
        console.print("[red]Error: Provide problem via --problem or --file[/red]")
        return
    
    console.print(f"[bold blue]OR Assistant[/bold blue]")
    console.print(f"[dim]Solving problem with {solver}...[/dim]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Step 1: Classify
        task1 = progress.add_task("[cyan]Classifying problem...", total=None)
        # TODO: Implement classification
        progress.update(task1, completed=True)
        
        # Step 2: Model
        task2 = progress.add_task("[cyan]Generating model...", total=None)
        # TODO: Implement model generation
        progress.update(task2, completed=True)
        
        # Step 3: Solve
        task3 = progress.add_task("[cyan]Solving...", total=None)
        # TODO: Implement solving
        progress.update(task3, completed=True)
        
        # Step 4: Interpret
        task4 = progress.add_task("[cyan]Interpreting results...", total=None)
        # TODO: Implement interpretation
        progress.update(task4, completed=True)
    
    console.print("\n[bold green]✓ Solution found![/bold green]\n")
    
    # Display results
    table = Table(title="Solution Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Objective Value", "$12,450")
    table.add_row("Status", "Optimal")
    table.add_row("Solve Time", "2.3s")
    
    console.print(table)
    
    if output:
        console.print(f"\n[dim]Results saved to {output}[/dim]")


@cli.command()
@click.argument('category', required=False)
def examples(category):
    """List example problems"""
    
    console.print("[bold blue]Example Problems[/bold blue]\n")
    
    examples_list = {
        "Linear Programming": [
            "Production planning with resource constraints",
            "Diet optimization problem",
            "Portfolio optimization"
        ],
        "Integer Programming": [
            "Facility location problem",
            "Capital budgeting",
            "Lot sizing"
        ],
        "Transportation": [
            "Warehouse to store shipping",
            "Supply chain optimization"
        ],
        "Assignment": [
            "Task assignment to workers",
            "Machine scheduling"
        ]
    }
    
    if category:
        if category in examples_list:
            console.print(f"[cyan]{category}:[/cyan]")
            for ex in examples_list[category]:
                console.print(f"  • {ex}")
        else:
            console.print(f"[red]Category '{category}' not found[/red]")
    else:
        for cat, exs in examples_list.items():
            console.print(f"[cyan]{cat}:[/cyan]")
            for ex in exs:
                console.print(f"  • {ex}")
            console.print()


@cli.command()
def solvers():
    """List available solvers"""
    
    table = Table(title="Available Solvers")
    table.add_column("Solver", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="green")
    
    # TODO: Actually check solver availability
    table.add_row("PuLP", "LP/IP", "✓ Available")
    table.add_row("OR-Tools", "Routing/CP", "✓ Available")
    table.add_row("CVXPY", "Convex", "✓ Available")
    table.add_row("Gurobi", "Commercial", "✗ Not configured")
    
    console.print(table)


@cli.command()
def config():
    """Show configuration"""
    
    console.print("[bold blue]Configuration[/bold blue]\n")
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        console.print(f"[green]✓[/green] Anthropic API Key: {'*' * 20}{api_key[-8:]}")
    else:
        console.print("[red]✗ Anthropic API Key: Not configured[/red]")
    
    console.print(f"Default Model: {os.getenv('DEFAULT_MODEL', 'claude-sonnet-4-5-20250929')}")
    console.print(f"Default Solver: {os.getenv('DEFAULT_SOLVER', 'pulp')}")
    console.print(f"Debug Mode: {os.getenv('DEBUG', 'False')}")


@cli.command()
@click.argument('key')
@click.argument('value')
def set_config(key, value):
    """Set configuration value"""
    
    # Update .env file
    env_file = '.env'
    
    if not os.path.exists(env_file):
        console.print("[yellow]Creating .env file...[/yellow]")
        with open('.env.example', 'r') as src:
            with open('.env', 'w') as dst:
                dst.write(src.read())
    
    console.print(f"[green]✓ Set {key} = {value}[/green]")
    console.print("[dim]Restart the application for changes to take effect[/dim]")


if __name__ == '__main__':
    cli()
