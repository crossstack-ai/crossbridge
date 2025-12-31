"""
Governance layer for AI operations.

Provides cost tracking, audit logging, credit management, and safety validation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai.base import (
    CostLimitExceededError,
    CreditExhaustedError,
    SafetyViolationError,
)
from core.ai.models import (
    AIExecutionContext,
    AIResponse,
    AuditEntry,
    CreditBalance,
    ExecutionStatus,
    SafetyLevel,
    TaskType,
    TokenUsage,
)


class CostTracker:
    """
    Track AI operation costs and usage.
    
    Provides real-time cost tracking and budget enforcement.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            storage_path: Path to store cost data
        """
        self.storage_path = storage_path or Path("data/ai/costs")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._daily_costs: Dict[str, float] = {}
        self._monthly_costs: Dict[str, float] = {}
        self._total_cost: float = 0.0
        
        self._load_costs()
    
    def _load_costs(self):
        """Load cost data from storage."""
        costs_file = self.storage_path / "costs.json"
        if costs_file.exists():
            try:
                with open(costs_file, "r") as f:
                    data = json.load(f)
                    self._daily_costs = data.get("daily", {})
                    self._monthly_costs = data.get("monthly", {})
                    self._total_cost = data.get("total", 0.0)
            except:
                pass
    
    def _save_costs(self):
        """Save cost data to storage."""
        costs_file = self.storage_path / "costs.json"
        with open(costs_file, "w") as f:
            json.dump({
                "daily": self._daily_costs,
                "monthly": self._monthly_costs,
                "total": self._total_cost,
                "last_updated": datetime.now().isoformat(),
            }, f, indent=2)
    
    def record_cost(
        self,
        cost: float,
        context: AIExecutionContext,
        response: AIResponse,
    ):
        """
        Record cost for an AI operation.
        
        Args:
            cost: Cost in dollars
            context: Execution context
            response: AI response
        """
        # Track total
        self._total_cost += cost
        
        # Track by date
        date_key = datetime.now().strftime("%Y-%m-%d")
        month_key = datetime.now().strftime("%Y-%m")
        
        self._daily_costs[date_key] = self._daily_costs.get(date_key, 0.0) + cost
        self._monthly_costs[month_key] = self._monthly_costs.get(month_key, 0.0) + cost
        
        # Save to disk
        self._save_costs()
    
    def check_budget(self, context: AIExecutionContext, estimated_cost: float) -> bool:
        """
        Check if operation would exceed budget.
        
        Args:
            context: Execution context with cost limits
            estimated_cost: Estimated cost of operation
        
        Returns:
            True if within budget, False otherwise
        """
        # Check max cost limit
        if context.max_cost and estimated_cost > context.max_cost:
            return False
        
        return True
    
    def enforce_budget(self, context: AIExecutionContext, estimated_cost: float):
        """
        Enforce budget limits, raise exception if exceeded.
        
        Args:
            context: Execution context
            estimated_cost: Estimated cost
        
        Raises:
            CostLimitExceededError: If cost limit exceeded
        """
        if not self.check_budget(context, estimated_cost):
            raise CostLimitExceededError(
                f"Estimated cost ${estimated_cost:.4f} exceeds limit ${context.max_cost:.4f}"
            )
    
    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific day."""
        date_key = (date or datetime.now()).strftime("%Y-%m-%d")
        return self._daily_costs.get(date_key, 0.0)
    
    def get_monthly_cost(self, date: Optional[datetime] = None) -> float:
        """Get total cost for a specific month."""
        month_key = (date or datetime.now()).strftime("%Y-%m")
        return self._monthly_costs.get(month_key, 0.0)
    
    def get_total_cost(self) -> float:
        """Get total cost across all time."""
        return self._total_cost
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of costs."""
        return {
            "total": self._total_cost,
            "today": self.get_daily_cost(),
            "this_month": self.get_monthly_cost(),
            "daily_breakdown": dict(sorted(self._daily_costs.items(), reverse=True)[:30]),
            "monthly_breakdown": dict(sorted(self._monthly_costs.items(), reverse=True)[:12]),
        }


class AuditLog:
    """
    Audit logging for all AI operations.
    
    Provides compliance, debugging, and analysis capabilities.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize audit log.
        
        Args:
            storage_path: Path to store audit logs
        """
        self.storage_path = storage_path or Path("data/ai/audit")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def log(
        self,
        context: AIExecutionContext,
        response: AIResponse,
        prompt_version: Optional[str] = None,
    ):
        """
        Log an AI operation.
        
        Args:
            context: Execution context
            response: AI response
            prompt_version: Prompt template version used
        """
        entry = AuditEntry(
            execution_id=context.execution_id,
            task_type=context.task_type,
            project_id=context.project_id,
            user=context.user,
            provider=response.provider,
            model=response.model,
            prompt_version=prompt_version,
            token_usage=response.token_usage,
            cost=response.cost,
            latency=response.latency,
            status=response.status,
            error=response.error,
            metadata=context.metadata,
        )
        
        # Write to file
        self._write_entry(entry)
    
    def _write_entry(self, entry: AuditEntry):
        """Write audit entry to storage."""
        # Organize by date
        date_key = entry.timestamp.strftime("%Y-%m-%d")
        log_file = self.storage_path / f"{date_key}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
    
    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        task_type: Optional[TaskType] = None,
        user: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[AuditEntry]:
        """
        Query audit logs.
        
        Args:
            start_date: Start date for query
            end_date: End date for query
            task_type: Filter by task type
            user: Filter by user
            project_id: Filter by project
        
        Returns:
            List of matching audit entries
        """
        entries = []
        
        # Default to last 30 days
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        # Iterate through date range
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            log_file = self.storage_path / f"{date_key}.jsonl"
            
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            
                            # Apply filters
                            if task_type and data.get("task_type") != task_type.value:
                                continue
                            if user and data.get("user") != user:
                                continue
                            if project_id and data.get("project_id") != project_id:
                                continue
                            
                            entries.append(self._parse_entry(data))
                        except:
                            continue
            
            current_date += timedelta(days=1)
        
        return entries
    
    def _parse_entry(self, data: Dict[str, Any]) -> AuditEntry:
        """Parse audit entry from dict."""
        token_usage_data = data.get("token_usage")
        token_usage = None
        if token_usage_data:
            token_usage = TokenUsage(**token_usage_data)
        
        return AuditEntry(
            audit_id=data.get("audit_id", ""),
            execution_id=data.get("execution_id", ""),
            task_type=TaskType(data.get("task_type", "test_generation")),
            project_id=data.get("project_id"),
            user=data.get("user"),
            provider=data.get("provider", "openai"),
            model=data.get("model", ""),
            prompt_version=data.get("prompt_version"),
            token_usage=token_usage,
            cost=data.get("cost", 0.0),
            latency=data.get("latency", 0.0),
            status=ExecutionStatus(data.get("status", "completed")),
            error=data.get("error"),
            safety_violations=data.get("safety_violations", []),
            content_filtered=data.get("content_filtered", False),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )
    
    def get_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics."""
        entries = self.query(start_date=start_date, end_date=end_date)
        
        total_cost = sum(e.cost for e in entries)
        total_tokens = sum(
            e.token_usage.total_tokens if e.token_usage else 0 for e in entries
        )
        total_latency = sum(e.latency for e in entries)
        
        by_task = {}
        by_provider = {}
        
        for entry in entries:
            # By task type
            task_key = entry.task_type.value
            if task_key not in by_task:
                by_task[task_key] = {"count": 0, "cost": 0.0, "tokens": 0}
            by_task[task_key]["count"] += 1
            by_task[task_key]["cost"] += entry.cost
            by_task[task_key]["tokens"] += (
                entry.token_usage.total_tokens if entry.token_usage else 0
            )
            
            # By provider
            provider_key = entry.provider.value if hasattr(entry.provider, 'value') else str(entry.provider)
            if provider_key not in by_provider:
                by_provider[provider_key] = {"count": 0, "cost": 0.0, "tokens": 0}
            by_provider[provider_key]["count"] += 1
            by_provider[provider_key]["cost"] += entry.cost
            by_provider[provider_key]["tokens"] += (
                entry.token_usage.total_tokens if entry.token_usage else 0
            )
        
        return {
            "total_operations": len(entries),
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_latency": total_latency,
            "average_latency": total_latency / len(entries) if entries else 0,
            "by_task_type": by_task,
            "by_provider": by_provider,
        }


class CreditManager:
    """
    Manage AI credits for users and projects.
    
    Provides credit-based billing and quota enforcement.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize credit manager.
        
        Args:
            storage_path: Path to store credit data
        """
        self.storage_path = storage_path or Path("data/ai/credits")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._balances: Dict[str, CreditBalance] = {}
        self._load_balances()
    
    def _load_balances(self):
        """Load credit balances from storage."""
        balances_file = self.storage_path / "balances.json"
        if balances_file.exists():
            try:
                with open(balances_file, "r") as f:
                    data = json.load(f)
                    for user_id, balance_data in data.items():
                        self._balances[user_id] = CreditBalance(
                            user_id=user_id,
                            project_id=balance_data.get("project_id"),
                            total_credits=balance_data.get("total_credits", 0.0),
                            used_credits=balance_data.get("used_credits", 0.0),
                            daily_limit=balance_data.get("daily_limit"),
                            monthly_limit=balance_data.get("monthly_limit"),
                            daily_used=balance_data.get("daily_used", 0.0),
                            monthly_used=balance_data.get("monthly_used", 0.0),
                        )
            except:
                pass
    
    def _save_balances(self):
        """Save credit balances to storage."""
        balances_file = self.storage_path / "balances.json"
        data = {}
        for user_id, balance in self._balances.items():
            data[user_id] = {
                "user_id": balance.user_id,
                "project_id": balance.project_id,
                "total_credits": balance.total_credits,
                "used_credits": balance.used_credits,
                "daily_limit": balance.daily_limit,
                "monthly_limit": balance.monthly_limit,
                "daily_used": balance.daily_used,
                "monthly_used": balance.monthly_used,
                "last_reset": balance.last_reset.isoformat(),
            }
        
        with open(balances_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def get_balance(self, user_id: str, project_id: Optional[str] = None) -> CreditBalance:
        """Get credit balance for user/project."""
        key = f"{user_id}:{project_id}" if project_id else user_id
        
        if key not in self._balances:
            self._balances[key] = CreditBalance(
                user_id=user_id,
                project_id=project_id,
            )
        
        return self._balances[key]
    
    def add_credits(
        self,
        user_id: str,
        amount: float,
        project_id: Optional[str] = None,
    ):
        """Add credits to user/project balance."""
        balance = self.get_balance(user_id, project_id)
        balance.total_credits += amount
        self._save_balances()
    
    def consume_credits(
        self,
        user_id: str,
        amount: float,
        project_id: Optional[str] = None,
    ):
        """
        Consume credits for an operation.
        
        Args:
            user_id: User identifier
            amount: Amount to consume
            project_id: Optional project identifier
        
        Raises:
            CreditExhaustedError: If insufficient credits
        """
        balance = self.get_balance(user_id, project_id)
        
        if not balance.can_consume(amount):
            raise CreditExhaustedError(
                f"Insufficient credits. Available: {balance.available_credits:.4f}, "
                f"Required: {amount:.4f}"
            )
        
        balance.consume(amount)
        self._save_balances()
    
    def check_credits(
        self,
        context: AIExecutionContext,
        estimated_cost: float,
    ) -> bool:
        """
        Check if user has sufficient credits.
        
        Args:
            context: Execution context
            estimated_cost: Estimated cost
        
        Returns:
            True if sufficient credits available
        """
        if not context.user:
            return True  # No user, no credit check
        
        balance = self.get_balance(context.user, context.project_id)
        return balance.can_consume(estimated_cost)
    
    def enforce_credits(
        self,
        context: AIExecutionContext,
        estimated_cost: float,
    ):
        """
        Enforce credit limits.
        
        Args:
            context: Execution context
            estimated_cost: Estimated cost
        
        Raises:
            CreditExhaustedError: If insufficient credits
        """
        if not self.check_credits(context, estimated_cost):
            balance = self.get_balance(context.user, context.project_id)
            raise CreditExhaustedError(
                f"Insufficient credits for {context.user}. "
                f"Available: {balance.available_credits:.4f}, "
                f"Required: {estimated_cost:.4f}"
            )


class SafetyValidator:
    """
    Validate AI inputs and outputs for safety.
    
    Prevents injection attacks, inappropriate content, and leaks.
    """
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.MODERATE):
        """
        Initialize safety validator.
        
        Args:
            safety_level: Level of safety checking
        """
        self.safety_level = safety_level
    
    def validate_input(self, inputs: Dict[str, Any], context: AIExecutionContext):
        """
        Validate inputs for safety issues.
        
        Args:
            inputs: Input data to validate
            context: Execution context
        
        Raises:
            SafetyViolationError: If safety issues detected
        """
        if self.safety_level == SafetyLevel.PERMISSIVE:
            return  # Skip validation
        
        # Check for secrets/API keys in inputs
        for key, value in inputs.items():
            value_str = str(value).lower()
            
            if any(keyword in value_str for keyword in ["api_key", "password", "secret", "token"]):
                if any(pattern in value for pattern in ["sk-", "ghp_", "Bearer"]):
                    raise SafetyViolationError(
                        f"Potential secret detected in input field '{key}'"
                    )
        
        # Check for injection attempts
        dangerous_patterns = [
            "system:",
            "ignore previous",
            "disregard",
            "new instructions",
        ]
        
        if self.safety_level == SafetyLevel.STRICT:
            for key, value in inputs.items():
                value_str = str(value).lower()
                for pattern in dangerous_patterns:
                    if pattern in value_str:
                        raise SafetyViolationError(
                            f"Potential prompt injection detected in field '{key}'"
                        )
    
    def validate_output(self, response: AIResponse, context: AIExecutionContext):
        """
        Validate AI output for safety issues.
        
        Args:
            response: AI response to validate
            context: Execution context
        
        Raises:
            SafetyViolationError: If safety issues detected
        """
        if self.safety_level == SafetyLevel.PERMISSIVE:
            return
        
        # Check for potential leaks in output
        content = response.content.lower()
        
        # Check for API keys/secrets
        if any(pattern in response.content for pattern in ["sk-", "ghp_", "Bearer "]):
            raise SafetyViolationError(
                "Potential secret leaked in AI output"
            )
