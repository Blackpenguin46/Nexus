#!/usr/bin/env python3
"""
Command Line Interface for the Manus Agent.

This module provides a user-friendly CLI for interacting with the autonomous agent,
including task execution, status monitoring, and configuration management.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .api.server import create_app
from .core.agent import ManusAgent
from .core.config import Config
from .core.exceptions import ConfigurationError, ManusError
from .utils.logger import get_logger


console = Console()
logger = get_logger(__name__)


class ManusCliError(Exception):
    """CLI-specific error."""
    pass


async def run_agent_interactive(agent: ManusAgent) -> None:
    """Run the agent in interactive mode."""
    console.print(Panel.fit(
        f"🤖 Manus Agent Interactive Mode\n"
        f"Session: {agent.state.session_id[:8]}...\n"
        f"Type 'help' for commands, 'exit' to quit",
        title="Manus Agent",
        border_style="blue"
    ))
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold blue]Manus[/bold blue]")
            
            if not user_input.strip():
                continue
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            elif user_input.lower() == 'help':
                show_help()
                continue
            elif user_input.lower() == 'status':
                show_status(agent)
                continue
            elif user_input.lower() == 'history':
                show_history(agent)
                continue
            elif user_input.lower() == 'clear':
                agent.clear_conversation()
                console.print("[green]Conversation cleared[/green]")
                continue
            elif user_input.lower() == 'reset':
                if Confirm.ask("Are you sure you want to reset the session?"):
                    await agent.reset_session()
                    console.print("[green]Session reset[/green]")
                continue
            
            # Execute task
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Executing task...", total=None)
                
                try:
                    result = await agent.execute_task(user_input)
                    progress.remove_task(task)
                    
                    # Display result
                    if result["success"]:
                        console.print(Panel(
                            result["result"],
                            title="✅ Task Completed",
                            border_style="green"
                        ))
                    else:
                        console.print(Panel(
                            result["result"],
                            title="❌ Task Failed",
                            border_style="red"
                        ))
                    
                    # Show execution info
                    console.print(f"[dim]Time: {result['execution_time']:.2f}s | "
                                f"Iterations: {result['iterations']}[/dim]")
                    
                except Exception as e:
                    progress.remove_task(task)
                    console.print(f"[red]Error: {e}[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
        except EOFError:
            break
    
    console.print("[yellow]Goodbye![/yellow]")


def show_help() -> None:
    """Show help information."""
    help_text = """
[bold]Available Commands:[/bold]

[blue]Task Execution:[/blue]
  - Just type your task and press Enter
  - Example: "Create a Python script to calculate fibonacci numbers"

[blue]Agent Commands:[/blue]
  - [bold]status[/bold]     Show agent status and metrics
  - [bold]history[/bold]    Show conversation history
  - [bold]clear[/bold]      Clear conversation history
  - [bold]reset[/bold]      Reset the entire session
  - [bold]help[/bold]       Show this help message
  - [bold]exit[/bold]       Exit the agent

[blue]Tips:[/blue]
  - Be specific about what you want to accomplish
  - The agent can work with files, browse the web, and execute code
  - All operations are sandboxed for security
"""
    console.print(Panel(help_text, title="Help", border_style="cyan"))


def show_status(agent: ManusAgent) -> None:
    """Show agent status."""
    status = agent.get_status()
    
    table = Table(title="Agent Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Session ID", status["session_id"][:16] + "...")
    table.add_row("Agent Version", status["agent_version"])
    table.add_row("Running", "Yes" if status["running"] else "No")
    table.add_row("Total Tasks", str(status["total_tasks"]))
    table.add_row("Total Iterations", str(status["total_iterations"]))
    table.add_row("Total Tool Calls", str(status["total_tool_calls"]))
    table.add_row("Total Errors", str(status["total_errors"]))
    table.add_row("Available Tools", str(len(status["available_tools"])))
    
    console.print(table)
    
    if status["current_task"]["id"]:
        console.print(f"\n[bold]Current Task:[/bold] {status['current_task']['id'][:16]}...")
        console.print(f"Status: {status['current_task']['status']}")
        console.print(f"Iteration: {status['current_task']['iteration']}")


def show_history(agent: ManusAgent) -> None:
    """Show conversation history."""
    history = agent.get_conversation_history(limit=10)
    
    if not history:
        console.print("[dim]No conversation history[/dim]")
        return
    
    table = Table(title="Recent Conversation History")
    table.add_column("Time", style="cyan")
    table.add_column("Role", style="blue") 
    table.add_column("Content", style="white")
    table.add_column("Tools", style="green")
    
    for msg in history[-10:]:  # Show last 10 messages
        content = msg["content"][:80] + "..." if len(msg["content"]) > 80 else msg["content"]
        time_str = msg["timestamp"][:19].replace("T", " ")
        
        table.add_row(
            time_str,
            msg["role"],
            content,
            str(msg["tool_calls"]) if msg["tool_calls"] > 0 else "-"
        )
    
    console.print(table)


async def run_single_task(agent: ManusAgent, task: str) -> int:
    """Run a single task and exit."""
    try:
        console.print(f"[blue]Executing task:[/blue] {task}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress_task = progress.add_task("Processing...", total=None)
            
            result = await agent.execute_task(task)
            progress.remove_task(progress_task)
        
        if result["success"]:
            console.print(Panel(
                result["result"],
                title="✅ Task Completed",
                border_style="green"
            ))
            return 0
        else:
            console.print(Panel(
                result["result"],
                title="❌ Task Failed", 
                border_style="red"
            ))
            return 1
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def run_web_server(host: str, port: int, config: Config) -> None:
    """Run the web API server."""
    console.print(f"[blue]Starting Manus web server on {host}:{port}[/blue]")
    
    app = create_app(config)
    
    config_dict = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info" if config.debug_mode else "warning",
        access_log=config.debug_mode,
    )
    
    server = uvicorn.Server(config_dict)
    await server.serve()


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manus - Autonomous AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  manus                                    # Interactive mode
  manus --task "Create a hello world app"  # Single task
  manus --web --port 8000                  # Web server mode
  manus --status                           # Show status only
        """
    )
    
    # Operation modes
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Execute a single task and exit"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        default=False,
        help="Run in interactive mode (default)"
    )
    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Run web API server"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show agent status and exit"
    )
    
    # Configuration
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="data/agent_state.json",
        help="Path to agent state file"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    # Web server options
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Web server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Web server port (default: 8000)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
        else:
            config = Config.from_env()
        
        if args.debug:
            config.debug_mode = True
            config.logging.level = "DEBUG"
        
        # Validate configuration
        config.validate_runtime()
        
        # Run the appropriate mode
        return asyncio.run(_run_main(args, config))
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration Error:[/red] {e.message}")
        if e.details:
            console.print(f"[dim]Details: {e.details}[/dim]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if args.debug:
            import traceback
            console.print(traceback.format_exc())
        return 1


async def _run_main(args: argparse.Namespace, config: Config) -> int:
    """Main async function."""
    if args.web:
        await run_web_server(args.host, args.port, config)
        return 0
    
    # Create agent
    async with ManusAgent(config, args.state_file) as agent:
        if args.status:
            show_status(agent)
            return 0
        
        if args.task:
            return await run_single_task(agent, args.task)
        
        # Default to interactive mode
        await run_agent_interactive(agent)
        return 0


if __name__ == "__main__":
    sys.exit(main())