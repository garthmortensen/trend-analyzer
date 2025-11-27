from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

def create_analysis_progress():
    """Creates a progress bar for the analysis iterations."""
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )

def log_step(message, style=None):
    """Logs a step to the console."""
    console.log(message, style=style)

def print_banner():
    """Prints the application banner."""
    banner = """
    ....................................................................................
    ▄▄▄▄▄▄ ▄▄▄▄  ▄▄▄▄▄ ▄▄  ▄▄ ▄▄▄▄         ▄▄▄  ▄▄  ▄▄  ▄▄▄  ▄▄  ▄▄ ▄▄ ▄▄▄▄▄ ▄▄▄▄▄ ▄▄▄▄
      ██   ██▄█▄ ██▄▄  ███▄██ ██▀██ g▄▄▄m ██▀██ ███▄██ ██▀██ ██  ▀███▀   ▄█▀ ██▄▄  ██▄█▄
      ██   ██ ██ ██▄▄▄ ██ ▀██ ████▀       ██▀██ ██ ▀██ ██▀██ ██▄▄▄ █   ▄██▄▄ ██▄▄▄ ██ ██
    ...................................................................................."""
    console.print(f"[bold red]{banner}[/bold red]")
