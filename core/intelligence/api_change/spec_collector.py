"""
OpenAPI Spec Collector

Collects OpenAPI/Swagger specifications from various sources:
- Local files (YAML/JSON)
- URLs (HTTP endpoints)
- Git commits
- CI artifacts
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import requests
import yaml
import json
import subprocess
import logging

logger = logging.getLogger(__name__)


class SpecCollector:
    """Collect OpenAPI specs from various sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize spec collector
        
        Args:
            config: Spec source configuration
        """
        self.config = config
        self.source_type = config.get("type", "file")
    
    def collect_specs(self) -> Tuple[Dict, Dict, str, str]:
        """
        Collect current and previous specs
        
        Returns:
            Tuple of (current_spec, previous_spec, current_version, previous_version)
        """
        logger.info(f"Collecting specs from source type: {self.source_type}")
        
        try:
            if self.source_type == "file":
                return self._collect_from_files()
            elif self.source_type == "url":
                return self._collect_from_urls()
            elif self.source_type == "git":
                return self._collect_from_git()
            elif self.source_type == "auto":
                return self._collect_auto()
            else:
                raise ValueError(f"Unsupported source type: {self.source_type}")
        except Exception as e:
            logger.error(f"Failed to collect specs: {e}")
            raise
    
    def _collect_from_files(self) -> Tuple[Dict, Dict, str, str]:
        """Load specs from local files"""
        current_path = Path(self.config["current"])
        previous_path = Path(self.config["previous"])
        
        logger.info(f"Loading current spec from: {current_path}")
        logger.info(f"Loading previous spec from: {previous_path}")
        
        if not current_path.exists():
            raise FileNotFoundError(f"Current spec not found: {current_path}")
        if not previous_path.exists():
            raise FileNotFoundError(f"Previous spec not found: {previous_path}")
        
        current = self._load_spec_file(current_path)
        previous = self._load_spec_file(previous_path)
        
        # Extract versions from specs
        current_version = self._extract_version(current, str(current_path))
        previous_version = self._extract_version(previous, str(previous_path))
        
        return current, previous, current_version, previous_version
    
    def _collect_from_urls(self) -> Tuple[Dict, Dict, str, str]:
        """Download specs from URLs"""
        url_config = self.config.get("url", {})
        headers = url_config.get("headers", {})
        
        current_url = url_config.get("current")
        previous_url = url_config.get("previous")
        
        if not current_url or not previous_url:
            raise ValueError("Both current and previous URLs must be specified")
        
        logger.info(f"Downloading current spec from: {current_url}")
        logger.info(f"Downloading previous spec from: {previous_url}")
        
        current = self._download_spec(current_url, headers)
        previous = self._download_spec(previous_url, headers)
        
        current_version = self._extract_version(current, current_url)
        previous_version = self._extract_version(previous, previous_url)
        
        return current, previous, current_version, previous_version
    
    def _collect_from_git(self) -> Tuple[Dict, Dict, str, str]:
        """Extract specs from Git commits"""
        git_config = self.config.get("git", {})
        repo = git_config.get("repo", ".")
        spec_path = git_config.get("spec_path")
        current_commit = git_config.get("current_commit", "HEAD")
        previous_commit = git_config.get("previous_commit", "HEAD~1")
        
        if not spec_path:
            raise ValueError("spec_path must be specified for git source type")
        
        logger.info(f"Extracting spec from Git: {spec_path}")
        logger.info(f"Current commit: {current_commit}")
        logger.info(f"Previous commit: {previous_commit}")
        
        current = self._get_file_from_git(repo, spec_path, current_commit)
        previous = self._get_file_from_git(repo, spec_path, previous_commit)
        
        current_version = self._extract_version(current, f"{current_commit}:{spec_path}")
        previous_version = self._extract_version(previous, f"{previous_commit}:{spec_path}")
        
        return current, previous, current_version, previous_version
    
    def _collect_auto(self) -> Tuple[Dict, Dict, str, str]:
        """Auto-detect source type and collect"""
        # Try file first
        if "current" in self.config and "previous" in self.config:
            current_path = Path(self.config["current"])
            if current_path.exists():
                self.source_type = "file"
                return self._collect_from_files()
        
        # Try URL
        if "url" in self.config:
            self.source_type = "url"
            return self._collect_from_urls()
        
        # Try Git
        if "git" in self.config:
            self.source_type = "git"
            return self._collect_from_git()
        
        raise ValueError("Could not auto-detect spec source. Please specify type explicitly.")
    
    def _load_spec_file(self, path: Path) -> Dict:
        """Load spec from file (YAML or JSON)"""
        content = path.read_text(encoding="utf-8")
        
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(content)
        elif path.suffix == ".json":
            return json.loads(content)
        else:
            # Try to parse as YAML first, then JSON
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError:
                return json.loads(content)
    
    def _download_spec(self, url: str, headers: Dict) -> Dict:
        """Download spec from URL"""
        # Expand environment variables in headers
        expanded_headers = {}
        for key, value in headers.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                import os
                env_var = value[2:-1]
                expanded_headers[key] = os.environ.get(env_var, "")
            else:
                expanded_headers[key] = value
        
        response = requests.get(url, headers=expanded_headers, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            return response.json()
        else:
            # Try YAML first, fallback to JSON
            try:
                return yaml.safe_load(response.text)
            except yaml.YAMLError:
                return response.json()
    
    def _get_file_from_git(self, repo: str, file_path: str, commit: str) -> Dict:
        """Get file content from specific Git commit"""
        cmd = ["git", "-C", repo, "show", f"{commit}:{file_path}"]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}") from e
        
        # Parse based on file extension
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(result.stdout)
        else:
            return json.loads(result.stdout)
    
    def _extract_version(self, spec: Dict, source: str) -> str:
        """Extract version from OpenAPI spec"""
        # Try OpenAPI 3.x info.version
        if "info" in spec and "version" in spec["info"]:
            return spec["info"]["version"]
        
        # Try Swagger 2.0 info.version
        if "swagger" in spec and "info" in spec and "version" in spec["info"]:
            return spec["info"]["version"]
        
        # Fallback to source identifier
        return source
    
    def get_spec_info(self, spec: Dict) -> Dict[str, str]:
        """Extract metadata from spec"""
        info = {
            "version": "unknown",
            "title": "unknown",
            "description": "",
            "openapi_version": "unknown",
        }
        
        if "openapi" in spec:
            info["openapi_version"] = spec["openapi"]
        elif "swagger" in spec:
            info["openapi_version"] = spec["swagger"]
        
        if "info" in spec:
            spec_info = spec["info"]
            info["version"] = spec_info.get("version", "unknown")
            info["title"] = spec_info.get("title", "unknown")
            info["description"] = spec_info.get("description", "")
        
        return info
