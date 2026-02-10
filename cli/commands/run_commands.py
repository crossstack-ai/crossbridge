"""
CrossBridge Test Runner Commands

Pure Python implementation of crossbridge-run functionality.
Wraps test execution with CrossBridge monitoring for any supported framework.
"""

import typer
import sys
import os
import subprocess
import requests
import json
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel

console = Console()

run_app = typer.Typer(
    name="run",
    help="Execute tests with CrossBridge monitoring"
)


class CrossBridgeRunner:
    """Manages test execution with CrossBridge monitoring."""
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "robot": ["robot", "pybot"],
        "pytest": ["pytest", "py.test"],
        "jest": ["jest"],
        "mocha": ["mocha", "_mocha"],
        "junit": ["mvn", "maven"],
    }
    
    def __init__(self):
        self.sidecar_host = os.getenv("CROSSBRIDGE_SIDECAR_HOST", "localhost")
        self.sidecar_port = os.getenv("CROSSBRIDGE_SIDECAR_PORT", "8765")
        self.enabled = os.getenv("CROSSBRIDGE_ENABLED", "true").lower() == "true"
        self.adapter_dir = os.getenv(
            "CROSSBRIDGE_ADAPTER_DIR",
            str(Path.home() / ".crossbridge" / "adapters")
        )
        
        # Backward compatibility
        if os.getenv("CROSSBRIDGE_API_HOST"):
            self.sidecar_host = os.getenv("CROSSBRIDGE_API_HOST")
        if os.getenv("CROSSBRIDGE_API_PORT"):
            self.sidecar_port = os.getenv("CROSSBRIDGE_API_PORT")
        
        self.sidecar_url = f"http://{self.sidecar_host}:{self.sidecar_port}"
    
    def check_sidecar(self) -> bool:
        """Check if sidecar is reachable."""
        try:
            response = requests.get(f"{self.sidecar_url}/health", timeout=2)
            if response.status_code == 200:
                console.print(
                    f"[green]✅ Connected to CrossBridge sidecar at "
                    f"{self.sidecar_host}:{self.sidecar_port}[/green]"
                )
                return True
        except Exception:
            pass
        
        console.print(
            f"[yellow]⚠️  Cannot reach CrossBridge sidecar at "
            f"{self.sidecar_host}:{self.sidecar_port}[/yellow]"
        )
        console.print("[yellow]Tests will run without CrossBridge monitoring[/yellow]")
        self.enabled = False
        return False
    
    def detect_framework(self, command: str, *args) -> str:
        """Detect test framework from command."""
        # Direct command match
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            if command in patterns:
                return framework
        
        # npm/yarn special handling
        if command in ["npm", "yarn"]:
            if len(args) > 0 and (args[0] == "test" or (args[0] == "run" and len(args) > 1 and args[1] == "test")):
                # Try to detect from package.json
                if Path("package.json").exists():
                    try:
                        with open("package.json") as f:
                            pkg = json.load(f)
                            if "jest" in json.dumps(pkg):
                                return "jest"
                            elif "mocha" in json.dumps(pkg):
                                return "mocha"
                    except Exception:
                        pass
        
        return "unknown"
    
    def download_adapter(self, framework: str) -> bool:
        """Download adapter from sidecar."""
        adapter_path = Path(self.adapter_dir) / framework
        
        # Skip if adapter exists and is recent (< 24 hours)
        if adapter_path.exists():
            age_seconds = (
                Path().stat().st_mtime - adapter_path.stat().st_mtime
                if adapter_path.stat().st_mtime else 86400
            )
            if age_seconds < 86400:
                console.print(f"[green]Using cached {framework} adapter[/green]")
                return True
        
        console.print(f"[blue]Downloading {framework} adapter from sidecar...[/blue]")
        
        adapter_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response = requests.get(
                f"{self.sidecar_url}/adapters/{framework}",
                timeout=30
            )
            
            if response.status_code == 200:
                tar_file = adapter_path.parent / f"{framework}.tar.gz"
                tar_file.write_bytes(response.content)
                
                # Extract tar
                import tarfile
                with tarfile.open(tar_file) as tar:
                    tar.extractall(adapter_path.parent)
                
                tar_file.unlink()
                console.print(f"[green]✅ {framework} adapter downloaded[/green]")
                return True
            else:
                console.print(f"[red]Failed to download {framework} adapter[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Failed to download {framework} adapter: {e}[/red]")
            return False
    
    def setup_robot(self, adapter_path: Path) -> dict:
        """Setup Robot Framework integration."""
        if not adapter_path.exists():
            if not self.download_adapter("robot"):
                return {}
        
        console.print("[green]Robot Framework configured with CrossBridge listener[/green]")
        
        return {
            "env": {
                "PYTHONPATH": f"{adapter_path}:{os.getenv('PYTHONPATH', '')}",
            },
            "args_prefix": ["--listener", "crossbridge_listener.CrossBridgeListener"]
        }
    
    def setup_pytest(self, adapter_path: Path) -> dict:
        """Setup Pytest integration."""
        if not adapter_path.exists():
            if not self.download_adapter("pytest"):
                return {}
        
        console.print("[green]Pytest configured with CrossBridge plugin[/green]")
        
        return {
            "env": {
                "PYTHONPATH": f"{adapter_path}:{os.getenv('PYTHONPATH', '')}",
                "PYTEST_PLUGINS": "crossbridge_plugin"
            }
        }
    
    def setup_jest(self, adapter_path: Path, args: List[str]) -> dict:
        """Setup Jest integration."""
        if not adapter_path.exists():
            if not self.download_adapter("jest"):
                return {}
        
        console.print("[green]Jest configured with CrossBridge reporter[/green]")
        
        # Add reporter if not already present
        extra_args = []
        if "--reporters" not in " ".join(args):
            reporter_path = adapter_path / "crossbridge_reporter.js"
            extra_args = [
                "--reporters=default",
                f"--reporters={reporter_path}"
            ]
        
        return {"args_suffix": extra_args}
    
    def setup_mocha(self, adapter_path: Path, args: List[str]) -> dict:
        """Setup Mocha integration."""
        if not adapter_path.exists():
            if not self.download_adapter("mocha"):
                return {}
        
        console.print("[green]Mocha configured with CrossBridge reporter[/green]")
        
        # Add reporter if not already present
        extra_args = []
        if "--reporter" not in " ".join(args):
            reporter_path = adapter_path / "crossbridge_reporter.js"
            extra_args = ["--reporter", str(reporter_path)]
        
        return {"args_suffix": extra_args}
    
    def setup_junit(self, adapter_path: Path) -> dict:
        """Setup JUnit/Maven integration."""
        if not adapter_path.exists():
            if not self.download_adapter("junit"):
                return {}
        
        console.print(f"[yellow]JUnit adapter downloaded to {adapter_path}[/yellow]")
        console.print(
            f"[yellow]Please add CrossBridgeListener to your test configuration[/yellow]"
        )
        console.print(f"[yellow]See: {adapter_path}/README.md for instructions[/yellow]")
        
        return {}
    
    def run_tests(self, command: List[str]) -> int:
        """Execute tests with CrossBridge monitoring."""
        if not command:
            console.print("[red]Error: No test command specified[/red]")
            return 1
        
        # Export configuration
        os.environ["CROSSBRIDGE_ENABLED"] = str(self.enabled)
        os.environ["CROSSBRIDGE_SIDECAR_HOST"] = self.sidecar_host
        os.environ["CROSSBRIDGE_SIDECAR_PORT"] = str(self.sidecar_port)
        
        # Check sidecar
        self.check_sidecar()
        
        if not self.enabled:
            console.print("[yellow]Running tests without CrossBridge monitoring[/yellow]")
            return subprocess.call(command)
        
        # Detect framework
        framework = self.detect_framework(command[0], *command[1:])
        
        if framework == "unknown":
            console.print(f"[yellow]Unknown test framework: {command[0]}[/yellow]")
            console.print("[yellow]Running tests without CrossBridge monitoring[/yellow]")
            return subprocess.call(command)
        
        console.print(f"[green]Detected framework: {framework}[/green]")
        
        # Setup framework-specific integration
        adapter_path = Path(self.adapter_dir) / framework
        setup_config = {}
        
        if framework == "robot":
            setup_config = self.setup_robot(adapter_path)
        elif framework == "pytest":
            setup_config = self.setup_pytest(adapter_path)
        elif framework == "jest":
            setup_config = self.setup_jest(adapter_path, command[1:])
        elif framework == "mocha":
            setup_config = self.setup_mocha(adapter_path, command[1:])
        elif framework == "junit":
            setup_config = self.setup_junit(adapter_path)
        
        # Build final command
        final_command = command.copy()
        
        # Add args prefix (for Robot Framework --listener)
        if "args_prefix" in setup_config:
            final_command = [command[0]] + setup_config["args_prefix"] + command[1:]
        
        # Add args suffix (for Jest/Mocha reporters)
        if "args_suffix" in setup_config:
            final_command = final_command + setup_config["args_suffix"]
        
        # Merge environment variables
        env = os.environ.copy()
        if "env" in setup_config:
            env.update(setup_config["env"])
        
        # Execute tests
        return subprocess.call(final_command, env=env)


@run_app.callback(invoke_without_command=True)
def run_callback(
    ctx: typer.Context,
    command: Optional[List[str]] = typer.Argument(None, help="Test command and arguments")
):
    """
    Execute tests with CrossBridge monitoring.
    
    Automatically injects CrossBridge monitoring into any supported test framework.
    
    \b
    Examples:
        crossbridge run robot tests/
        crossbridge run pytest tests/
        crossbridge run jest tests/
        crossbridge run mocha tests/
        crossbridge run mvn test
    
    \b
    Supported Frameworks:
        - Robot Framework (robot, pybot)
        - Pytest (pytest, py.test)
        - Jest (jest, npm test)
        - Mocha (mocha)
        - JUnit/Maven (mvn test)
    
    \b
    Environment Variables:
        CROSSBRIDGE_SIDECAR_HOST   - Sidecar API host (default: localhost)
        CROSSBRIDGE_SIDECAR_PORT   - Sidecar API port (default: 8765)
        CROSSBRIDGE_ENABLED        - Enable/disable CrossBridge (default: true)
        CROSSBRIDGE_ADAPTER_DIR    - Adapter cache directory (default: ~/.crossbridge/adapters)
    """
    if not command:
        console.print(Panel(
            "[yellow]Usage: crossbridge run <test-command> [args...][/yellow]\n\n"
            "Run 'crossbridge run --help' for more information",
            title="CrossBridge Test Runner"
        ))
        raise typer.Exit(0)
    
    runner = CrossBridgeRunner()
    exit_code = runner.run_tests(command)
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    run_app()
