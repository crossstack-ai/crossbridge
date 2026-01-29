"""
OASDiff Engine Wrapper

Wraps the oasdiff CLI tool for comparing OpenAPI specifications
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries=3, backoff_factor=2, exceptions=(subprocess.TimeoutExpired, subprocess.CalledProcessError)):
    """Decorator to retry function calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator


class OASDiffEngine:
    """Wrapper for oasdiff CLI tool"""
    
    def __init__(self, oasdiff_path: str = "oasdiff"):
        """
        Initialize OASDiff engine
        
        Args:
            oasdiff_path: Path to oasdiff binary (default: "oasdiff" in PATH)
        """
        self.oasdiff_path = oasdiff_path
        self._check_oasdiff_installed()
    
    def _check_oasdiff_installed(self):
        """Verify oasdiff is installed and accessible"""
        try:
            result = subprocess.run(
                [self.oasdiff_path, "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            version = result.stdout.decode().strip()
            logger.info(f"oasdiff version: {version}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("oasdiff command timed out")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "oasdiff not found. Install it:\n"
                "  go install github.com/tufin/oasdiff@latest\n"
                "Or download from: https://github.com/tufin/oasdiff/releases"
            )
    
    def diff(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any],
        include_checks: bool = True,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Compare two OpenAPI specs using oasdiff
        
        Args:
            old_spec: Previous OpenAPI spec as dictionary
            new_spec: Current OpenAPI spec as dictionary
            include_checks: Include breaking change checks
            format: Output format (json, yaml, text, html)
        
        Returns:
            Parsed diff result as dictionary
        """
        logger.info("Running oasdiff comparison...")
        
        # Write specs to temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"
            
            # Write as YAML for better oasdiff compatibility
            old_path.write_text(yaml.dump(old_spec, sort_keys=False))
            new_path.write_text(yaml.dump(new_spec, sort_keys=False))
            
            # Build command
            cmd = [
                self.oasdiff_path,
                "diff",
                str(old_path),
                str(new_path),
                "-f", format
            ]
            
            if include_checks:
                cmd.extend(["-c", "all"])
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run oasdiff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't fail on differences (exit code 1)
                timeout=60
            )
            
            # Exit codes:
            # 0 = no differences
            # 1 = differences found
            # 2+ = error
            if result.returncode >= 2:
                logger.error(f"oasdiff failed with exit code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                raise RuntimeError(f"oasdiff failed: {result.stderr}")
            
            if result.returncode == 0:
                logger.info("No differences found")
                return {"paths": {}, "schemas": {}, "summary": {"total": 0}}
            
            logger.info(f"Differences found (exit code: {result.returncode})")
            
            # Parse output
            if format == "json":
                if result.stdout:
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON output: {e}")
                        logger.debug(f"Raw output: {result.stdout}")
                        return {"paths": {}, "schemas": {}, "raw_output": result.stdout}
                else:
                    return {"paths": {}, "schemas": {}}
            else:
                # For non-JSON formats, return raw output
                return {"raw_output": result.stdout}
    
    def diff_breaking(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect breaking changes only
        
        Args:
            old_spec: Previous OpenAPI spec
            new_spec: Current OpenAPI spec
        
        Returns:
            List of breaking changes
        """
        logger.info("Checking for breaking changes...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"
            
            old_path.write_text(yaml.dump(old_spec, sort_keys=False))
            new_path.write_text(yaml.dump(new_spec, sort_keys=False))
            
            cmd = [
                self.oasdiff_path,
                "breaking",
                str(old_path),
                str(new_path),
                "-f", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("No breaking changes found")
                return []
            
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    breaking_changes = data.get("breaking", [])
                    logger.info(f"Found {len(breaking_changes)} breaking changes")
                    return breaking_changes
                except json.JSONDecodeError:
                    logger.error("Failed to parse breaking changes output")
                    return []
            else:
                return []
    
    def changelog(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any],
        format: str = "markdown"
    ) -> str:
        """
        Generate changelog between two specs
        
        Args:
            old_spec: Previous spec
            new_spec: Current spec
            format: Output format (markdown, text)
        
        Returns:
            Changelog text
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"
            
            old_path.write_text(yaml.dump(old_spec, sort_keys=False))
            new_path.write_text(yaml.dump(new_spec, sort_keys=False))
            
            cmd = [
                self.oasdiff_path,
                "changelog",
                str(old_path),
                str(new_path)
            ]
            
            if format == "markdown":
                cmd.append("--format=markdown")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )
            
            return result.stdout if result.stdout else "No changes"
    
    def summary(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Get summary statistics of changes
        
        Args:
            old_spec: Previous spec
            new_spec: Current spec
        
        Returns:
            Dictionary with change counts
        """
        diff_result = self.diff(old_spec, new_spec, include_checks=False)
        breaking_changes = self.diff_breaking(old_spec, new_spec)
        
        summary = {
            "total_changes": 0,
            "breaking_changes": len(breaking_changes),
            "added_endpoints": 0,
            "modified_endpoints": 0,
            "removed_endpoints": 0,
            "schema_changes": 0,
        }
        
        # Count endpoint changes
        if "paths" in diff_result:
            for path, methods in diff_result["paths"].items():
                if isinstance(methods, dict):
                    for method, changes in methods.items():
                        summary["total_changes"] += 1
                        if "added" in changes or changes.get("added"):
                            summary["added_endpoints"] += 1
                        elif "deleted" in changes or changes.get("deleted"):
                            summary["removed_endpoints"] += 1
                        elif "modified" in changes or changes.get("modified"):
                            summary["modified_endpoints"] += 1
        
        # Count schema changes
        if "schemas" in diff_result:
            summary["schema_changes"] = len(diff_result["schemas"])
            summary["total_changes"] += summary["schema_changes"]
        
        return summary
