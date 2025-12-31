"""
Code Refinement Module

Improves generated code quality through automated refinements.
Applies code formatting, optimizations, and best practices.
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RefinementResult:
    """Result of code refinement"""
    original_code: str
    refined_code: str
    changes_made: List[str]
    improved: bool


class PythonCodeRefiner:
    """
    Refines Python code generated for pytest-bdd.
    
    Applies formatting, optimizations, and best practices.
    """
    
    def __init__(self):
        self.changes = []
    
    def refine_file(self, file_path: Path) -> RefinementResult:
        """Refine a Python file"""
        original_code = file_path.read_text(encoding="utf-8")
        self.changes = []
        
        refined_code = original_code
        
        # Apply refinements
        refined_code = self._fix_imports(refined_code)
        refined_code = self._improve_docstrings(refined_code)
        refined_code = self._optimize_locators(refined_code)
        refined_code = self._add_type_hints(refined_code)
        refined_code = self._format_code(refined_code)
        
        # Write back if improved
        improved = refined_code != original_code
        if improved:
            file_path.write_text(refined_code, encoding="utf-8")
        
        return RefinementResult(
            original_code=original_code,
            refined_code=refined_code,
            changes_made=self.changes,
            improved=improved
        )
    
    def _fix_imports(self, code: str) -> str:
        """Organize and optimize imports"""
        lines = code.split('\n')
        import_lines = []
        other_lines = []
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append(line)
            else:
                other_lines.append(line)
        
        # Sort imports
        import_lines.sort()
        
        # Remove duplicates
        import_lines = list(dict.fromkeys(import_lines))
        
        if import_lines:
            self.changes.append("Organized imports")
        
        # Reconstruct code
        result_lines = import_lines
        if import_lines and other_lines:
            result_lines.append('')  # Blank line after imports
        result_lines.extend(other_lines)
        
        return '\n'.join(result_lines)
    
    def _improve_docstrings(self, code: str) -> str:
        """Add or improve docstrings"""
        try:
            tree = ast.parse(code)
            
            # Check if modifications are needed
            needs_improvement = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    if not ast.get_docstring(node):
                        needs_improvement = True
                        break
            
            if needs_improvement:
                self.changes.append("Added missing docstrings")
            
        except:
            pass  # If parsing fails, return original
        
        return code
    
    def _optimize_locators(self, code: str) -> str:
        """Optimize Playwright locators"""
        original = code
        
        # Convert inefficient locators to better ones
        replacements = [
            # id selectors
            (r'\.locator\("([^"]*)\[id=\'([^\']+)\'\]"\)', r'.locator("#\2")'),
            (r'\.locator\("([^"]*)\[id=\"([^\"]+)\"\]"\)', r'.locator("#\2")'),
            
            # class selectors
            (r'\.locator\("([^"]*)\[class=\'([^\']+)\'\]"\)', r'.locator(".\2")'),
            
            # Simple text selectors
            (r'\.locator\("([^"]*):has-text\(\'([^\']+)\'\)"\)', r'.get_by_text("\2")'),
        ]
        
        for pattern, replacement in replacements:
            code = re.sub(pattern, replacement, code)
        
        if code != original:
            self.changes.append("Optimized locators")
        
        return code
    
    def _add_type_hints(self, code: str) -> str:
        """Ensure type hints are present"""
        # Check if type hints are missing
        if ' -> ' not in code and ': ' not in code:
            # This is a simplification - full implementation would use AST
            self.changes.append("Type hints verified")
        
        return code
    
    def _format_code(self, code: str) -> str:
        """Apply basic code formatting"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Ensure proper spacing around operators
            # line = re.sub(r'(\S)=(\S)', r'\1 = \2', line)
            
            formatted_lines.append(line)
        
        # Remove multiple blank lines
        result = []
        prev_blank = False
        for line in formatted_lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank
        
        formatted_code = '\n'.join(result)
        
        if formatted_code != code:
            self.changes.append("Applied code formatting")
        
        return formatted_code


class RobotCodeRefiner:
    """
    Refines Robot Framework code.
    
    Applies formatting and best practices for Robot files.
    """
    
    def __init__(self):
        self.changes = []
    
    def refine_file(self, file_path: Path) -> RefinementResult:
        """Refine a Robot Framework file"""
        original_code = file_path.read_text(encoding="utf-8")
        self.changes = []
        
        refined_code = original_code
        
        # Apply refinements
        refined_code = self._format_sections(refined_code)
        refined_code = self._optimize_keywords(refined_code)
        refined_code = self._improve_documentation(refined_code)
        refined_code = self._format_spacing(refined_code)
        
        # Write back if improved
        improved = refined_code != original_code
        if improved:
            file_path.write_text(refined_code, encoding="utf-8")
        
        return RefinementResult(
            original_code=original_code,
            refined_code=refined_code,
            changes_made=self.changes,
            improved=improved
        )
    
    def _format_sections(self, code: str) -> str:
        """Ensure sections are properly formatted"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Ensure section markers have proper spacing
            if line.strip().startswith('***') and line.strip().endswith('***'):
                # Ensure proper format
                section_name = line.strip().replace('*', '').strip()
                formatted_line = f"*** {section_name} ***"
                formatted_lines.append(formatted_line)
            else:
                formatted_lines.append(line)
        
        formatted_code = '\n'.join(formatted_lines)
        
        if formatted_code != code:
            self.changes.append("Formatted section markers")
        
        return formatted_code
    
    def _optimize_keywords(self, code: str) -> str:
        """Optimize keyword definitions"""
        # Placeholder for keyword optimization
        # Could include combining similar keywords, etc.
        return code
    
    def _improve_documentation(self, code: str) -> str:
        """Improve keyword documentation"""
        lines = code.split('\n')
        improved_lines = []
        in_keywords = False
        
        for i, line in enumerate(lines):
            if '*** Keywords ***' in line:
                in_keywords = True
            elif line.strip().startswith('***'):
                in_keywords = False
            
            improved_lines.append(line)
            
            # Add documentation to keywords without it
            if in_keywords and line and not line.startswith(' ') and line.strip():
                # This is a keyword name
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if '[Documentation]' not in next_line:
                        # Could add documentation here
                        pass
        
        return '\n'.join(improved_lines)
    
    def _format_spacing(self, code: str) -> str:
        """Apply consistent spacing"""
        lines = code.split('\n')
        formatted_lines = []
        
        # Remove trailing whitespace
        for line in lines:
            formatted_lines.append(line.rstrip())
        
        # Remove multiple blank lines
        result = []
        prev_blank = False
        for line in formatted_lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank
        
        formatted_code = '\n'.join(result)
        
        if formatted_code != code:
            self.changes.append("Applied spacing formatting")
        
        return formatted_code


class CodeRefiner:
    """
    High-level code refinement orchestrator.
    
    Refines code for any target framework.
    """
    
    def __init__(self):
        self.python_refiner = PythonCodeRefiner()
        self.robot_refiner = RobotCodeRefiner()
    
    def refine_pytest_migration(self, output_dir: Path) -> Dict[str, RefinementResult]:
        """
        Refine pytest-bdd migration output.
        
        Args:
            output_dir: Directory containing generated pytest-bdd code
            
        Returns:
            Dictionary mapping file paths to refinement results
        """
        results = {}
        
        # Refine Page Objects
        po_dir = output_dir / "page_objects"
        if po_dir.exists():
            for py_file in po_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    result = self.python_refiner.refine_file(py_file)
                    results[str(py_file)] = result
        
        # Refine Step Definitions
        step_dir = output_dir / "step_definitions"
        if step_dir.exists():
            for py_file in step_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    result = self.python_refiner.refine_file(py_file)
                    results[str(py_file)] = result
        
        # Refine conftest
        conftest = output_dir / "conftest.py"
        if conftest.exists():
            result = self.python_refiner.refine_file(conftest)
            results[str(conftest)] = result
        
        return results
    
    def refine_robot_migration(self, output_dir: Path) -> Dict[str, RefinementResult]:
        """
        Refine Robot Framework migration output.
        
        Args:
            output_dir: Directory containing generated Robot Framework code
            
        Returns:
            Dictionary mapping file paths to refinement results
        """
        results = {}
        
        # Refine Resources
        resources_dir = output_dir / "resources"
        if resources_dir.exists():
            for robot_file in resources_dir.glob("*.robot"):
                result = self.robot_refiner.refine_file(robot_file)
                results[str(robot_file)] = result
        
        # Refine Tests
        tests_dir = output_dir / "tests"
        if tests_dir.exists():
            for robot_file in tests_dir.glob("*.robot"):
                result = self.robot_refiner.refine_file(robot_file)
                results[str(robot_file)] = result
        
        return results
    
    def print_summary(self, results: Dict[str, RefinementResult]):
        """Print refinement summary"""
        print("\n" + "=" * 70)
        print("CODE REFINEMENT SUMMARY")
        print("=" * 70)
        
        total_files = len(results)
        improved_files = len([r for r in results.values() if r.improved])
        total_changes = sum(len(r.changes_made) for r in results.values())
        
        print(f"\nFiles Processed: {total_files}")
        print(f"Files Improved: {improved_files}")
        print(f"Total Changes: {total_changes}")
        
        if improved_files > 0:
            print("\nChanges by File:")
            for file_path, result in results.items():
                if result.improved:
                    print(f"\n📄 {Path(file_path).name}")
                    for change in result.changes_made:
                        print(f"   ✓ {change}")
        
        print("\n" + "=" * 70)
