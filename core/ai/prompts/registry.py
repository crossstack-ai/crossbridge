"""
Prompt registry and template management system.

Provides versioned, auditable prompt templates with Jinja2 rendering.
"""

import yaml
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai.models import ModelConfig, PromptTemplate


class PromptRegistry:
    """
    Central registry for versioned prompt templates.
    
    Templates are stored as YAML files and can be versioned for
    rollback, A/B testing, and auditability.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize prompt registry.
        
        Args:
            templates_dir: Directory containing prompt template YAML files
        """
        self.templates_dir = templates_dir or (
            Path(__file__).parent / "templates"
        )
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self._cache: Dict[str, Dict[str, PromptTemplate]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all templates from disk."""
        if not self.templates_dir.exists():
            return
        
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                template = PromptTemplate(
                    template_id=data["id"],
                    version=data["version"],
                    description=data["description"],
                    system_prompt=data["system_prompt"],
                    user_prompt_template=data["user_prompt"],
                    input_schema=data.get("input_schema", {}),
                    output_schema=data.get("output_schema", {}),
                    author=data.get("author"),
                    tags=data.get("tags", []),
                    default_model_config=self._parse_model_config(
                        data.get("model_config", {})
                    ),
                )
                
                # Cache by ID and version
                if template.template_id not in self._cache:
                    self._cache[template.template_id] = {}
                
                self._cache[template.template_id][template.version] = template
            
            except Exception as e:
                print(f"Warning: Failed to load template {template_file}: {e}")
    
    def _parse_model_config(self, config_data: Dict[str, Any]) -> Optional[ModelConfig]:
        """Parse model config from YAML data."""
        if not config_data:
            return None
        
        return ModelConfig(
            model=config_data.get("model", "gpt-4"),
            temperature=config_data.get("temperature", 0.7),
            max_tokens=config_data.get("max_tokens", 2048),
            top_p=config_data.get("top_p", 1.0),
            frequency_penalty=config_data.get("frequency_penalty", 0.0),
            presence_penalty=config_data.get("presence_penalty", 0.0),
            stop_sequences=config_data.get("stop_sequences", []),
            timeout=config_data.get("timeout", 60),
        )
    
    def get(
        self, template_id: str, version: Optional[str] = None
    ) -> PromptTemplate:
        """
        Get a prompt template by ID and version.
        
        Args:
            template_id: Template identifier
            version: Template version (if None, gets latest)
        
        Returns:
            PromptTemplate instance
        
        Raises:
            KeyError: If template not found
        """
        if template_id not in self._cache:
            raise KeyError(f"Template not found: {template_id}")
        
        versions = self._cache[template_id]
        
        if version is None:
            # Get latest version
            version = max(versions.keys())
        
        if version not in versions:
            raise KeyError(
                f"Version {version} not found for template {template_id}"
            )
        
        return versions[version]
    
    def register(self, template: PromptTemplate, save: bool = True):
        """
        Register a new prompt template.
        
        Args:
            template: Template to register
            save: Whether to save to disk
        """
        if template.template_id not in self._cache:
            self._cache[template.template_id] = {}
        
        self._cache[template.template_id][template.version] = template
        
        if save:
            self.save_template(template)
    
    def save_template(self, template: PromptTemplate):
        """
        Save template to disk as YAML.
        
        Args:
            template: Template to save
        """
        filename = f"{template.template_id}_{template.version}.yaml"
        filepath = self.templates_dir / filename
        
        data = {
            "id": template.template_id,
            "version": template.version,
            "description": template.description,
            "system_prompt": template.system_prompt,
            "user_prompt": template.user_prompt_template,
            "input_schema": template.input_schema,
            "output_schema": template.output_schema,
            "author": template.author,
            "tags": template.tags,
        }
        
        if template.default_model_config:
            data["model_config"] = {
                "model": template.default_model_config.model,
                "temperature": template.default_model_config.temperature,
                "max_tokens": template.default_model_config.max_tokens,
                "top_p": template.default_model_config.top_p,
                "frequency_penalty": template.default_model_config.frequency_penalty,
                "presence_penalty": template.default_model_config.presence_penalty,
                "stop_sequences": template.default_model_config.stop_sequences,
                "timeout": template.default_model_config.timeout,
            }
        
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def list_templates(self) -> List[str]:
        """Get list of all template IDs."""
        return list(self._cache.keys())
    
    def list_versions(self, template_id: str) -> List[str]:
        """
        Get list of versions for a template.
        
        Args:
            template_id: Template identifier
        
        Returns:
            List of version strings
        """
        if template_id not in self._cache:
            return []
        
        return list(self._cache[template_id].keys())
    
    def delete(self, template_id: str, version: str):
        """
        Delete a template version.
        
        Args:
            template_id: Template identifier
            version: Version to delete
        """
        if template_id in self._cache and version in self._cache[template_id]:
            del self._cache[template_id][version]
            
            # Delete from disk
            filename = f"{template_id}_{version}.yaml"
            filepath = self.templates_dir / filename
            if filepath.exists():
                filepath.unlink()


class PromptRenderer:
    """
    Render prompt templates with Jinja2.
    
    Handles template rendering with proper escaping and validation.
    """
    
    def __init__(self):
        """Initialize renderer with Jinja2 environment."""
        try:
            from jinja2 import Environment, StrictUndefined
            
            self.env = Environment(
                undefined=StrictUndefined,
                autoescape=False,  # Don't escape for prompts
                trim_blocks=True,
                lstrip_blocks=True,
            )
        except ImportError:
            raise ImportError(
                "Jinja2 not installed. Install with: pip install jinja2"
            )
    
    def render(
        self, template: PromptTemplate, inputs: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Render template with inputs.
        
        Args:
            template: Prompt template to render
            inputs: Input values for template variables
        
        Returns:
            List of messages (system + user) as dicts
        
        Raises:
            ValueError: If required inputs are missing
        """
        # Validate inputs
        self._validate_inputs(template, inputs)
        
        # Render system prompt
        system_prompt = template.system_prompt.strip()
        
        # Render user prompt
        user_template = self.env.from_string(template.user_prompt_template)
        user_prompt = user_template.render(**inputs).strip()
        
        # Return as message list
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def _validate_inputs(self, template: PromptTemplate, inputs: Dict[str, Any]):
        """
        Validate that required inputs are provided.
        
        Args:
            template: Prompt template
            inputs: Input values
        
        Raises:
            ValueError: If required inputs are missing
        """
        required_inputs = template.input_schema.get("required", [])
        
        missing = set(required_inputs) - set(inputs.keys())
        if missing:
            raise ValueError(
                f"Missing required inputs for template {template.template_id}: "
                f"{', '.join(missing)}"
            )


# Global registry instance
_registry: Optional[PromptRegistry] = None


def get_registry(templates_dir: Optional[Path] = None) -> PromptRegistry:
    """
    Get the global prompt registry instance.
    
    Args:
        templates_dir: Directory for templates (only used on first call)
    
    Returns:
        PromptRegistry instance
    """
    global _registry
    
    if _registry is None:
        _registry = PromptRegistry(templates_dir)
    
    return _registry


def get_prompt(template_id: str, version: Optional[str] = None) -> PromptTemplate:
    """
    Convenience function to get a prompt template.
    
    Args:
        template_id: Template identifier
        version: Template version (if None, gets latest)
    
    Returns:
        PromptTemplate instance
    """
    registry = get_registry()
    return registry.get(template_id, version)


def render_prompt(
    template_id: str, inputs: Dict[str, Any], version: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Convenience function to render a prompt.
    
    Args:
        template_id: Template identifier
        inputs: Input values for rendering
        version: Template version (if None, uses latest)
    
    Returns:
        List of rendered messages
    """
    registry = get_registry()
    template = registry.get(template_id, version)
    
    renderer = PromptRenderer()
    return renderer.render(template, inputs)
