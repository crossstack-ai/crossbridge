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
import tarfile
from pathlib import Path
from typing import Optional, List, Dict
from rich.console import Console
from rich.panel import Panel

from core.logging import get_logger, LogCategory
from core.sidecar.config import SidecarConfig

console = Console()
logger = get_logger(__name__, category=LogCategory.CLI)

run_app = typer.Typer(
    name="run",
    help="Execute tests with CrossBridge monitoring - Universal test wrapper that automatically injects monitoring into any supported framework"
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
            logger.debug(f"Checking sidecar health at {self.sidecar_url}/health")
            response = requests.get(f"{self.sidecar_url}/health", timeout=2)
            if response.status_code == 200:
                console.print(
                    f"[green]✅ Connected to CrossBridge sidecar at "
                    f"{self.sidecar_host}:{self.sidecar_port}[/green]"
                )
                logger.info(f"Sidecar health check successful: {self.sidecar_host}:{self.sidecar_port}")
                return True
            else:
                logger.warning(f"Sidecar health check failed with status {response.status_code}")
        except Exception as e:
            logger.warning(f"Sidecar health check failed: {e}")
        
        console.print(
            f"[yellow]⚠️  Cannot reach CrossBridge sidecar at "
            f"{self.sidecar_host}:{self.sidecar_port}[/yellow]"
        )
        console.print("[yellow]Tests will run without CrossBridge monitoring[/yellow]")
        logger.info("Disabling CrossBridge monitoring due to sidecar unavailability")
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
            import time
            age_seconds = time.time() - adapter_path.stat().st_mtime
            if age_seconds < 86400:
                console.print(f"[green]Using cached {framework} adapter[/green]")
                logger.debug(f"Using cached adapter for {framework} (age: {age_seconds:.0f}s)")
                return True
        
        console.print(f"[blue]Downloading {framework} adapter from sidecar...[/blue]")
        logger.info(f"Downloading {framework} adapter from {self.sidecar_url}")
        
        adapter_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            url = f"{self.sidecar_url}/adapters/{framework}"
            logger.debug(f"Requesting adapter from: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                tar_file = adapter_path.parent / f"{framework}.tar.gz"
                tar_file.write_bytes(response.content)
                logger.debug(f"Downloaded {len(response.content)} bytes to {tar_file}")
                
                # Extract tar
                with tarfile.open(tar_file) as tar:
                    tar.extractall(adapter_path.parent)
                    logger.debug(f"Extracted adapter to {adapter_path.parent}")
                
                tar_file.unlink()
                console.print(f"[green]✅ {framework} adapter downloaded[/green]")
                logger.info(f"Successfully downloaded and installed {framework} adapter")
                return True
            else:
                console.print(f"[red]Failed to download {framework} adapter[/red]")
                logger.error(f"Adapter download failed with status {response.status_code}")
                return False
        except Exception as e:
            console.print(f"[red]Failed to download {framework} adapter: {e}[/red]")
            logger.error(f"Adapter download exception: {e}", exc_info=True)
            return False
    
    def setup_robot(self, adapter_path: Path) -> Dict:
        """Setup Robot Framework integration."""
        if not adapter_path.exists():
            logger.info("Robot adapter not found, downloading...")
            if not self.download_adapter("robot"):
                logger.error("Failed to download Robot adapter")
                return {}
        
        console.print("[green]Robot Framework configured with CrossBridge listener[/green]")
        logger.info("Robot Framework configured with CrossBridge listener")
        
        return {
            "env": {
                "PYTHONPATH": f"{adapter_path}:{os.getenv('PYTHONPATH', '')}",
            },
            "args_prefix": ["--listener", "crossbridge_listener.CrossBridgeListener"]
        }
    
    def setup_pytest(self, adapter_path: Path) -> Dict:
        """Setup Pytest integration."""
        if not adapter_path.exists():
            logger.info("Pytest adapter not found, downloading...")
            if not self.download_adapter("pytest"):
                logger.error("Failed to download Pytest adapter")
                return {}
        
        console.print("[green]Pytest configured with CrossBridge plugin[/green]")
        logger.info("Pytest configured with CrossBridge plugin")
        
        return {
            "env": {
                "PYTHONPATH": f"{adapter_path}:{os.getenv('PYTHONPATH', '')}",
                "PYTEST_PLUGINS": "crossbridge_plugin"
            }
        }
    
    def setup_jest(self, adapter_path: Path, args: List[str]) -> Dict:
        """Setup Jest integration."""
        if not adapter_path.exists():
            logger.info("Jest adapter not found, downloading...")
            if not self.download_adapter("jest"):
                logger.error("Failed to download Jest adapter")
                return {}
        
        console.print("[green]Jest configured with CrossBridge reporter[/green]")
        logger.info("Jest configured with CrossBridge reporter")
        
        # Add reporter if not already present
        extra_args = []
        if "--reporters" not in " ".join(args):
            reporter_path = adapter_path / "crossbridge_reporter.js"
            extra_args = [
                "--reporters=default",
                f"--reporters={reporter_path}"
            ]
            logger.debug(f"Adding Jest reporters: {extra_args}")
        
        return {"args_suffix": extra_args}
    
    def setup_mocha(self, adapter_path: Path, args: List[str]) -> Dict:
        """Setup Mocha integration."""
        if not adapter_path.exists():
            logger.info("Mocha adapter not found, downloading...")
            if not self.download_adapter("mocha"):
                logger.error("Failed to download Mocha adapter")
                return {}
        
        console.print("[green]Mocha configured with CrossBridge reporter[/green]")
        logger.info("Mocha configured with CrossBridge reporter")
        
        # Add reporter if not already present
        extra_args = []
        if "--reporter" not in " ".join(args):
            reporter_path = adapter_path / "crossbridge_reporter.js"
            extra_args = ["--reporter", str(reporter_path)]
            logger.debug(f"Adding Mocha reporter: {reporter_path}")
        
        return {"args_suffix": extra_args}
    
    def setup_junit(self, adapter_path: Path) -> Dict:
        """Setup JUnit/Maven integration."""
        if not adapter_path.exists():
            logger.info("JUnit adapter not found, downloading...")
            if not self.download_adapter("junit"):
                logger.error("Failed to download JUnit adapter")
                return {}
        
        console.print(f"[yellow]JUnit adapter downloaded to {adapter_path}[/yellow]")
        console.print(
            f"[yellow]Please add CrossBridgeListener to your test configuration[/yellow]"
        )
        console.print(f"[yellow]See: {adapter_path}/README.md for instructions[/yellow]")
        logger.info(f"JUnit adapter ready at {adapter_path}")
        logger.info("Manual configuration required for JUnit integration")
        
        return {}
    
    def run_tests(self, command: List[str]) -> int:
        """Execute tests with CrossBridge monitoring."""
        if not command:
            console.print("[red]Error: No test command specified[/red]")
            logger.error("No test command specified")
            return 1
        
        # Export configuration
        os.environ["CROSSBRIDGE_ENABLED"] = str(self.enabled)
        os.environ["CROSSBRIDGE_SIDECAR_HOST"] = self.sidecar_host
        os.environ["CROSSBRIDGE_SIDECAR_PORT"] = str(self.sidecar_port)
        
        # Check sidecar
        self.check_sidecar()
        
        if not self.enabled:
            console.print("[yellow]Running tests without CrossBridge monitoring[/yellow]")
            logger.info("CrossBridge monitoring disabled - running tests directly")
            return subprocess.call(command)
        
        # Detect framework
        framework = self.detect_framework(command[0], *command[1:])
        
        if framework == "unknown":
            console.print(f"[yellow]Unknown test framework: {command[0]}[/yellow]")
            console.print("[yellow]Running tests without CrossBridge monitoring[/yellow]")
            logger.warning(f"Unknown test framework: {command[0]} - running without monitoring")
            return subprocess.call(command)
        
        console.print(f"[green]Detected framework: {framework}[/green]")
        logger.info(f"Detected framework: {framework}")
        
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
        
        logger.info(f"Framework setup complete: {framework}")
        
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
        
        logger.info(f"Executing command: {' '.join(final_command)}")
        # Execute tests
        return subprocess.call(final_command, env=env)


@run_app.callback(invoke_without_command=True)
def run_callback(
    ctx: typer.Context,
    command: Optional[List[str]] = typer.Argument(None, help="Test command and arguments"),
    sidecar_host: Optional[str] = typer.Option(
        None,
        "--sidecar-host",
        help="CrossBridge sidecar API host (default: localhost or CROSSBRIDGE_SIDECAR_HOST env var)"
    ),
    sidecar_port: Optional[int] = typer.Option(
        None,
        "--sidecar-port",
        help="CrossBridge sidecar API port (default: 8765 or CROSSBRIDGE_SIDECAR_PORT env var)"
    ),
    enabled: Optional[bool] = typer.Option(
        None,
        "--enabled/--no-enabled",
        help="Enable/disable CrossBridge monitoring (default: true or CROSSBRIDGE_ENABLED env var)"
    ),
    adapter_dir: Optional[str] = typer.Option(
        None,
        "--adapter-dir",
        help="Adapter cache directory (default: ~/.crossbridge/adapters or CROSSBRIDGE_ADAPTER_DIR env var)"
    ),
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
        crossbridge run --sidecar-host 192.168.1.100 pytest tests/
        crossbridge run --no-enabled pytest tests/  # Run without monitoring
    
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
    
    Note: Command-line options take precedence over environment variables.
    """
    if not command:
        console.print(Panel(
            "[yellow]Usage: crossbridge run [OPTIONS] <test-command> [args...][/yellow]\n\n"
            "Run 'crossbridge run --help' for more information\n\n"
            "[cyan]Examples:[/cyan]\n"
            "  crossbridge run robot tests/\n"
            "  crossbridge run pytest tests/\n"
            "  crossbridge run jest tests/\n"
            "  crossbridge run mocha tests/\n"
            "  crossbridge run mvn test\n\n"
            "[cyan]Supported Frameworks:[/cyan]\n"
            "  • Robot Framework (robot, pybot)\n"
            "  • Pytest (pytest, py.test)\n"
            "  • Jest (jest, npm test)\n"
            "  • Mocha (mocha)\n"
            "  • JUnit/Maven (mvn test)",
            title="CrossBridge Universal Test Wrapper",
            border_style="blue"
        ))
        raise typer.Exit(0)
    
    logger.info(f"Starting test execution: {' '.join(command)}")
    
    # Create runner and apply CLI options (which override env vars)
    runner = CrossBridgeRunner()
    
    if sidecar_host is not None:
        runner.sidecar_host = sidecar_host
        runner.sidecar_url = f"http://{runner.sidecar_host}:{runner.sidecar_port}"
    
    if sidecar_port is not None:
        runner.sidecar_port = str(sidecar_port)
        runner.sidecar_url = f"http://{runner.sidecar_host}:{runner.sidecar_port}"
    
    if enabled is not None:
        runner.enabled = enabled
    
    if adapter_dir is not None:
        runner.adapter_dir = adapter_dir
    
    exit_code = runner.run_tests(command)
    logger.info(f"Test execution completed with exit code: {exit_code}")
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    run_app()
