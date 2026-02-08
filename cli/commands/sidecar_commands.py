"""
Sidecar CLI Commands

Commands for managing remote sidecar observer and client.
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

from core.sidecar.observer import SidecarObserver
from core.sidecar.sampler import Sampler
from services.sidecar_api import SidecarAPIServer
from services.sidecar_client import create_remote_client_from_env
from cli.errors import CrossBridgeError

app = typer.Typer(
    name="sidecar",
    help="Remote sidecar observer and client management"
)

console = Console()


@app.command("start")
def start_sidecar(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to listen on"),
    framework: str = typer.Option("robot", "--framework", "-f", help="Test framework"),
    mode: str = typer.Option("observer", "--mode", "-m", help="Mode: observer or client"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Config file path")
):
    """
    Start sidecar observer or client
    
    Observer mode: Runs API server to receive events from remote test executions
    Client mode: Sends events to remote observer (requires CROSSBRIDGE_SIDECAR_HOST)
    
    Examples:
        # Start observer on port 8765
        crossbridge sidecar start --mode observer --port 8765
        
        # Start client (requires env vars)
        export CROSSBRIDGE_SIDECAR_HOST=10.60.67.247
        crossbridge sidecar start --mode client --framework pytest
    """
    if mode == "observer":
        console.print(f"[bold green]Starting CrossBridge Sidecar Observer[/bold green]")
        console.print(f"Host: {host}")
        console.print(f"Port: {port}")
        console.print(f"Framework: {framework}\n")
        
        try:
            # Initialize components
            sampler = Sampler(sample_rate=1.0)  # Sample all events
            observer = SidecarObserver(sampler=sampler)
            
            # Start observer
            observer.start()
            
            # Start API server
            api_server = SidecarAPIServer(
                observer=observer,
                host=host,
                port=port
            )
            
            console.print("[green]✓[/green] Sidecar observer started successfully")
            console.print(f"[cyan]→[/cyan] Listening on http://{host}:{port}")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
            
            # Run server (blocking)
            api_server.run()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            observer.stop()
            console.print("[green]✓[/green] Sidecar observer stopped")
            
        except Exception as e:
            raise CrossBridgeError(f"Failed to start sidecar observer: {e}")
    
    elif mode == "client":
        console.print(f"[bold green]Starting CrossBridge Sidecar Client[/bold green]")
        console.print(f"Framework: {framework}\n")
        
        try:
            # Create client from environment
            client = create_remote_client_from_env()
            
            if not client:
                raise CrossBridgeError(
                    "Remote sidecar not configured. Set CROSSBRIDGE_SIDECAR_HOST environment variable."
                )
            
            console.print("[green]✓[/green] Sidecar client started successfully")
            console.print(f"[cyan]→[/cyan] Sending events to {client.config.base_url}")
            console.print("[yellow]Client is running in background[/yellow]\n")
            
            # Keep running
            import time
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            if client:
                client.stop()
            console.print("[green]✓[/green] Sidecar client stopped")
            
        except Exception as e:
            raise CrossBridgeError(f"Failed to start sidecar client: {e}")
    
    else:
        raise CrossBridgeError(f"Invalid mode: {mode}. Must be 'observer' or 'client'")


@app.command("status")
def sidecar_status(
    host: str = typer.Option("localhost", "--host", "-h", help="Sidecar host"),
    port: int = typer.Option(8765, "--port", "-p", help="Sidecar port")
):
    """
    Check sidecar observer status
    
    Example:
        crossbridge sidecar status --host 10.60.67.247 --port 8765
    """
    import httpx
    
    url = f"http://{host}:{port}"
    
    console.print(f"[bold]Checking sidecar status at {url}...[/bold]\n")
    
    try:
        # Check health endpoint
        response = httpx.get(f"{url}/health", timeout=5)
        response.raise_for_status()
        
        health_data = response.json()
        
        # Display status
        table = Table(title="Sidecar Observer Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", health_data.get('status', 'unknown'))
        table.add_row("Version", health_data.get('version', 'unknown'))
        table.add_row("Mode", health_data.get('mode', 'unknown'))
        table.add_row("Uptime", f"{health_data.get('uptime_seconds', 0):.1f}s")
        table.add_row("Queue Size", str(health_data.get('queue_size', 0)))
        table.add_row("Events Processed", str(health_data.get('events_processed', 0)))
        table.add_row("Events Dropped", str(health_data.get('events_dropped', 0)))
        
        console.print(table)
        
        # Get stats
        stats_response = httpx.get(f"{url}/stats", timeout=5)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            
            console.print("\n[bold]Statistics:[/bold]")
            for key, value in stats.items():
                console.print(f"  {key}: {value}")
        
    except httpx.ConnectError:
        console.print(f"[red]✗[/red] Cannot connect to sidecar at {url}")
        console.print("[yellow]Is the sidecar observer running?[/yellow]")
    except Exception as e:
        raise CrossBridgeError(f"Failed to get sidecar status: {e}")


@app.command("test-connection")
def test_connection(
    host: str = typer.Option("localhost", "--host", "-h", help="Sidecar host"),
    port: int = typer.Option(8765, "--port", "-p", help="Sidecar port")
):
    """
    Test connection to remote sidecar
    
    Sends a test event to verify connectivity.
    
    Example:
        crossbridge sidecar test-connection --host 10.60.67.247
    """
    import httpx
    from datetime import datetime
    
    url = f"http://{host}:{port}"
    
    console.print(f"[bold]Testing connection to {url}...[/bold]\n")
    
    try:
        # Send test event
        test_event = {
            "event_type": "test.connection",
            "data": {
                "message": "Connection test from CrossBridge CLI",
                "timestamp": datetime.utcnow().isoformat()
            },
            "test_id": "test-connection",
            "framework": "crossbridge-cli"
        }
        
        response = httpx.post(f"{url}/events", json=test_event, timeout=5)
        response.raise_for_status()
        
        console.print("[green]✓[/green] Connection successful!")
        console.print(f"[cyan]Response:[/cyan] {response.json()}")
        
    except httpx.ConnectError:
        console.print(f"[red]✗[/red] Cannot connect to sidecar at {url}")
        console.print("[yellow]Check that:[/yellow]")
        console.print("  1. Sidecar observer is running")
        console.print("  2. Host and port are correct")
        console.print("  3. Firewall allows connections on port {port}")
    except Exception as e:
        raise CrossBridgeError(f"Connection test failed: {e}")


if __name__ == "__main__":
    app()
