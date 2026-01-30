"""
Code Reference Resolver

Resolves automation failure locations to actual code paths and snippets.
This is a KILLER FEATURE - shows exactly where test code failed.

Works by:
1. Parsing stack traces
2. Identifying first non-framework frame
3. Extracting file path and line number
4. Reading code snippet from workspace
5. Identifying function/class context

NO AI - pure deterministic parsing.
"""

import os
import re
from typing import Optional, List, Tuple
from pathlib import Path

from core.execution.intelligence.models import CodeReference, FailureSignal


class CodeReferenceResolver:
    """
    Resolves code references from stack traces.
    
    This helps developers pinpoint EXACTLY where their test code failed.
    """
    
    # Framework modules to skip when finding test code
    FRAMEWORK_MODULES = [
        'selenium',
        'pytest',
        'unittest',
        'robot',
        'playwright',
        '_pytest',
        'pluggy',
        'python3.',
        'lib/python',
        'site-packages',
        '/usr/lib',
        '/usr/local',
        'java.lang',
        'org.junit',
        'org.testng',
        'cucumber',
    ]
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize resolver.
        
        Args:
            workspace_root: Root directory of the test project
        """
        self.workspace_root = workspace_root or os.getcwd()
    
    def resolve(self, signal: FailureSignal) -> Optional[CodeReference]:
        """
        Resolve code reference from failure signal.
        
        Args:
            signal: Failure signal with stacktrace
            
        Returns:
            CodeReference or None if unable to resolve
        """
        if not signal.stacktrace:
            return None
        
        # Parse stacktrace
        frames = self._parse_stacktrace(signal.stacktrace)
        
        # Find first test code frame (skip framework code)
        test_frame = self._find_test_frame(frames)
        
        if not test_frame:
            return None
        
        file_path, line_num = test_frame
        
        # Read code snippet
        snippet = self._read_snippet(file_path, line_num)
        
        if not snippet:
            return None
        
        # Extract function/class context
        function, class_name = self._extract_context(file_path, line_num)
        
        # Get repository info
        repository = self._get_repository_info(file_path)
        commit = self._get_current_commit(file_path)
        
        return CodeReference(
            file=self._make_relative_path(file_path),
            line=line_num,
            snippet=snippet,
            function=function,
            class_name=class_name,
            repository=repository,
            commit=commit
        )
    
    def resolve_from_stacktrace(self, stacktrace: str) -> Optional[CodeReference]:
        """
        Resolve code reference directly from stacktrace string.
        
        Args:
            stacktrace: Raw stacktrace text
            
        Returns:
            CodeReference or None
        """
        frames = self._parse_stacktrace(stacktrace)
        test_frame = self._find_test_frame(frames)
        
        if not test_frame:
            return None
        
        file_path, line_num = test_frame
        snippet = self._read_snippet(file_path, line_num)
        
        if not snippet:
            return None
        
        function, class_name = self._extract_context(file_path, line_num)
        
        return CodeReference(
            file=self._make_relative_path(file_path),
            line=line_num,
            snippet=snippet,
            function=function,
            class_name=class_name
        )
    
    def _parse_stacktrace(self, stacktrace: str) -> List[Tuple[str, int]]:
        """
        Parse stacktrace into list of (file_path, line_number) tuples.
        
        Supports multiple stacktrace formats:
        - Python: File "path/file.py", line 42
        - Java: at package.Class.method(File.java:42)
        - JavaScript: at function (file.js:42:10)
        """
        frames = []
        
        # Python format: File "path/file.py", line 42
        python_pattern = r'File "([^"]+)", line (\d+)'
        for match in re.finditer(python_pattern, stacktrace):
            file_path = match.group(1)
            line_num = int(match.group(2))
            frames.append((file_path, line_num))
        
        # Java format: at package.Class.method(File.java:42)
        java_pattern = r'at .*?\(([^:]+):(\d+)\)'
        for match in re.finditer(java_pattern, stacktrace):
            file_path = match.group(1)
            line_num = int(match.group(2))
            frames.append((file_path, line_num))
        
        # JavaScript format: at function (file.js:42:10)
        js_pattern = r'at .*?\(([^:]+):(\d+):\d+\)'
        for match in re.finditer(js_pattern, stacktrace):
            file_path = match.group(1)
            line_num = int(match.group(2))
            frames.append((file_path, line_num))
        
        # Generic format: file.ext:42
        generic_pattern = r'([a-zA-Z0-9_/\\.-]+\.[a-zA-Z]+):(\d+)'
        for match in re.finditer(generic_pattern, stacktrace):
            file_path = match.group(1)
            line_num = int(match.group(2))
            # Only add if not already found by specific parsers
            if (file_path, line_num) not in frames:
                frames.append((file_path, line_num))
        
        return frames
    
    def _find_test_frame(self, frames: List[Tuple[str, int]]) -> Optional[Tuple[str, int]]:
        """
        Find first test code frame (skip framework code).
        
        Returns the first frame that:
        1. Is in the workspace
        2. Is not from a framework module
        3. Is readable
        """
        for file_path, line_num in frames:
            # Skip framework modules
            if any(fm in file_path.lower() for fm in self.FRAMEWORK_MODULES):
                continue
            
            # Try to make absolute path
            abs_path = self._resolve_file_path(file_path)
            
            if abs_path and os.path.isfile(abs_path):
                return abs_path, line_num
        
        return None
    
    def _resolve_file_path(self, file_path: str) -> Optional[str]:
        """Resolve relative file path to absolute path"""
        # Already absolute
        if os.path.isabs(file_path):
            if os.path.isfile(file_path):
                return file_path
            return None
        
        # Try relative to workspace root
        workspace_path = os.path.join(self.workspace_root, file_path)
        if os.path.isfile(workspace_path):
            return workspace_path
        
        # Try searching in workspace
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip common excluded directories
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']]
            
            if os.path.basename(file_path) in files:
                full_path = os.path.join(root, os.path.basename(file_path))
                if os.path.isfile(full_path):
                    return full_path
        
        return None
    
    def _read_snippet(self, file_path: str, line_num: int, context_lines: int = 5) -> Optional[str]:
        """
        Read code snippet around the specified line.
        
        Args:
            file_path: Absolute path to file
            line_num: Line number (1-indexed)
            context_lines: Number of lines before/after to include
            
        Returns:
            Code snippet or None
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Calculate range (1-indexed to 0-indexed)
            start_line = max(0, line_num - context_lines - 1)
            end_line = min(len(lines), line_num + context_lines)
            
            # Extract snippet
            snippet_lines = lines[start_line:end_line]
            
            # Add line numbers
            numbered_lines = []
            for i, line in enumerate(snippet_lines, start=start_line + 1):
                marker = '>>>' if i == line_num else '   '
                numbered_lines.append(f"{marker} {i:4d} | {line.rstrip()}")
            
            return '\n'.join(numbered_lines)
        
        except Exception:
            return None
    
    def _extract_context(self, file_path: str, line_num: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract function and class context for the line.
        
        Returns:
            (function_name, class_name) tuple
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            function_name = None
            class_name = None
            
            # Search backwards from the line to find function/class definitions
            for i in range(line_num - 1, -1, -1):
                line = lines[i].strip()
                
                # Python function
                if line.startswith('def '):
                    match = re.search(r'def\s+(\w+)', line)
                    if match and not function_name:
                        function_name = match.group(1)
                
                # Python class
                if line.startswith('class '):
                    match = re.search(r'class\s+(\w+)', line)
                    if match and not class_name:
                        class_name = match.group(1)
                        break  # Stop at class level
                
                # Java/JavaScript method
                if 'public' in line or 'private' in line or 'protected' in line:
                    match = re.search(r'(public|private|protected)\s+\w+\s+(\w+)\s*\(', line)
                    if match and not function_name:
                        function_name = match.group(2)
                
                # JavaScript function
                if 'function' in line:
                    match = re.search(r'function\s+(\w+)', line)
                    if match and not function_name:
                        function_name = match.group(1)
            
            return function_name, class_name
        
        except Exception:
            return None, None
    
    def _make_relative_path(self, file_path: str) -> str:
        """Convert absolute path to workspace-relative path"""
        try:
            return os.path.relpath(file_path, self.workspace_root)
        except ValueError:
            # Different drives on Windows
            return file_path
    
    def _get_repository_info(self, file_path: str) -> Optional[str]:
        """Get repository URL if in a git repository"""
        try:
            # Search for .git directory
            current_dir = os.path.dirname(file_path)
            while current_dir != os.path.dirname(current_dir):  # Not at root
                git_dir = os.path.join(current_dir, '.git')
                if os.path.isdir(git_dir):
                    # Try to read remote URL
                    config_file = os.path.join(git_dir, 'config')
                    if os.path.isfile(config_file):
                        with open(config_file, 'r') as f:
                            content = f.read()
                            match = re.search(r'url\s*=\s*(.+)', content)
                            if match:
                                return match.group(1).strip()
                    break
                current_dir = os.path.dirname(current_dir)
        except Exception:
            pass
        
        return None
    
    def _get_current_commit(self, file_path: str) -> Optional[str]:
        """Get current git commit hash"""
        try:
            # Search for .git directory
            current_dir = os.path.dirname(file_path)
            while current_dir != os.path.dirname(current_dir):
                git_dir = os.path.join(current_dir, '.git')
                if os.path.isdir(git_dir):
                    # Read HEAD
                    head_file = os.path.join(git_dir, 'HEAD')
                    if os.path.isfile(head_file):
                        with open(head_file, 'r') as f:
                            head_content = f.read().strip()
                            
                            # If HEAD is a ref, resolve it
                            if head_content.startswith('ref:'):
                                ref_path = head_content.split(':', 1)[1].strip()
                                ref_file = os.path.join(git_dir, ref_path)
                                if os.path.isfile(ref_file):
                                    with open(ref_file, 'r') as rf:
                                        return rf.read().strip()[:8]  # Short hash
                            else:
                                # Direct commit hash
                                return head_content[:8]
                    break
                current_dir = os.path.dirname(current_dir)
        except Exception:
            pass
        
        return None
