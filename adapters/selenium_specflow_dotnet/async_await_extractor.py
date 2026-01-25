"""
Async/await pattern detection and transformation for C# SpecFlow steps.

Handles asynchronous step definitions and async method calls.
"""

import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AsyncStepDefinition:
    """Represents an async step definition."""
    step_pattern: str
    method_name: str
    is_async: bool
    return_type: str
    awaited_calls: List[str]
    line_number: int


class CSharpAsyncAwaitExtractor:
    """Extract and analyze async/await patterns in C# code."""
    
    def __init__(self):
        # Async method pattern
        self.async_method_pattern = re.compile(
            r'\[(?:Given|When|Then|And|But)\("([^"]+)"\)\]\s*'
            r'public\s+async\s+(Task(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE | re.DOTALL
        )
        
        # Await pattern
        self.await_pattern = re.compile(
            r'await\s+([^\s;]+)',
            re.MULTILINE
        )
        
        # Task.Run pattern
        self.task_run_pattern = re.compile(
            r'Task\.Run\s*\(([^)]+)\)',
            re.DOTALL
        )
        
        # ConfigureAwait pattern
        self.configure_await_pattern = re.compile(
            r'\.ConfigureAwait\s*\(\s*(true|false)\s*\)',
            re.IGNORECASE
        )
    
    def extract_async_steps(
        self,
        cs_file: Path
    ) -> List[AsyncStepDefinition]:
        """
        Extract async step definitions from SpecFlow binding file.
        
        Args:
            cs_file: Path to C# file with step definitions
            
        Returns:
            List of AsyncStepDefinition objects
        """
        if not cs_file.exists():
            return []
        
        content = cs_file.read_text(encoding='utf-8')
        async_steps = []
        
        for match in self.async_method_pattern.finditer(content):
            step_pattern = match.group(1)
            return_type = match.group(2)
            method_name = match.group(3)
            line_num = content[:match.start()].count('\n') + 1
            
            # Find awaited calls in method body
            method_start = match.end()
            method_body = self._extract_method_body(content, method_start)
            awaited_calls = self._extract_awaited_calls(method_body)
            
            async_steps.append(AsyncStepDefinition(
                step_pattern=step_pattern,
                method_name=method_name,
                is_async=True,
                return_type=return_type,
                awaited_calls=awaited_calls,
                line_number=line_num
            ))
        
        return async_steps
    
    def _extract_method_body(self, content: str, start_pos: int) -> str:
        """Extract method body from start position."""
        # Find matching braces
        brace_count = 0
        in_method = False
        end_pos = start_pos
        
        for i in range(start_pos, len(content)):
            if content[i] == '{':
                brace_count += 1
                in_method = True
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0 and in_method:
                    end_pos = i
                    break
        
        return content[start_pos:end_pos]
    
    def _extract_awaited_calls(self, method_body: str) -> List[str]:
        """Extract all awaited method calls from method body."""
        awaited_calls = []
        
        for match in self.await_pattern.finditer(method_body):
            call = match.group(1)
            # Clean up the call (remove semicolons, ConfigureAwait, etc.)
            call = call.split(';')[0].strip()
            call = self.configure_await_pattern.sub('', call)
            awaited_calls.append(call)
        
        return awaited_calls
    
    def detect_async_patterns(self, cs_file: Path) -> Dict[str, int]:
        """
        Detect various async patterns in a file.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            Dictionary with pattern counts
        """
        if not cs_file.exists():
            return {}
        
        content = cs_file.read_text(encoding='utf-8')
        
        patterns = {
            'async_methods': len(re.findall(r'\basync\s+Task', content)),
            'await_calls': len(self.await_pattern.findall(content)),
            'task_run': len(self.task_run_pattern.findall(content)),
            'configure_await_true': len(re.findall(r'ConfigureAwait\s*\(\s*true\s*\)', content)),
            'configure_await_false': len(re.findall(r'ConfigureAwait\s*\(\s*false\s*\)', content)),
            'task_when_all': content.count('Task.WhenAll'),
            'task_when_any': content.count('Task.WhenAny'),
            'task_delay': content.count('Task.Delay'),
        }
        
        return patterns
    
    def has_async_steps(self, cs_file: Path) -> bool:
        """Check if file contains async step definitions."""
        async_steps = self.extract_async_steps(cs_file)
        return len(async_steps) > 0
    
    def convert_to_python_async(
        self,
        async_step: AsyncStepDefinition
    ) -> str:
        """
        Convert C# async step to Python async equivalent.
        
        Args:
            async_step: AsyncStepDefinition object
            
        Returns:
            Python async code
        """
        python_code = f"async def {async_step.method_name.lower()}():\n"
        python_code += f"    \"\"\" {async_step.step_pattern} \"\"\"\n"
        
        for awaited_call in async_step.awaited_calls:
            # Convert C# async call to Python
            python_call = self._convert_call_to_python(awaited_call)
            python_code += f"    result = await {python_call}\n"
        
        return python_code
    
    def _convert_call_to_python(self, csharp_call: str) -> str:
        """Convert C# method call to Python equivalent."""
        # Simplified conversion
        python_call = csharp_call
        
        # Convert common patterns
        conversions = {
            'HttpClient.GetAsync': 'client.get',
            'HttpClient.PostAsync': 'client.post',
            'Task.Delay': 'asyncio.sleep',
            'WebDriver.FindElementAsync': 'page.query_selector',
            'WebDriver.ClickAsync': 'element.click',
        }
        
        for csharp_pattern, python_pattern in conversions.items():
            if csharp_pattern in python_call:
                python_call = python_call.replace(csharp_pattern, python_pattern)
        
        return python_call
    
    def requires_async_support(self, project_root: Path) -> bool:
        """
        Check if project requires async/await support.
        
        Args:
            project_root: Root directory of project
            
        Returns:
            True if async patterns are found
        """
        for cs_file in project_root.rglob("*.cs"):
            if self.has_async_steps(cs_file):
                return True
        
        return False
    
    def get_async_complexity_score(self, cs_file: Path) -> int:
        """
        Calculate async complexity score for a file.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            Complexity score (0-100)
        """
        patterns = self.detect_async_patterns(cs_file)
        
        # Weight different patterns
        score = 0
        score += patterns.get('async_methods', 0) * 5
        score += patterns.get('await_calls', 0) * 3
        score += patterns.get('task_run', 0) * 4
        score += patterns.get('task_when_all', 0) * 8
        score += patterns.get('task_when_any', 0) * 10
        
        return min(score, 100)
    
    def generate_async_migration_notes(
        self,
        async_steps: List[AsyncStepDefinition]
    ) -> List[str]:
        """
        Generate migration notes for async steps.
        
        Args:
            async_steps: List of AsyncStepDefinition objects
            
        Returns:
            List of migration note strings
        """
        notes = []
        
        for step in async_steps:
            notes.append(
                f"Step '{step.step_pattern}' ({step.method_name}):\n"
                f"  - Async method with {len(step.awaited_calls)} awaited calls\n"
                f"  - Target: Python async/await or sync equivalent\n"
                f"  - Awaited operations: {', '.join(step.awaited_calls[:3])}"
            )
            
            if len(step.awaited_calls) > 5:
                notes.append(
                    f"  ⚠️ Complex async flow - consider refactoring"
                )
        
        return notes
