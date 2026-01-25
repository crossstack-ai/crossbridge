"""
LINQ pattern detection and transformation for C# tests.

Handles LINQ queries, lambda expressions, and functional patterns.
"""

import re
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class LinqExpression:
    """Represents a LINQ expression in C# code."""
    expression_type: str  # 'query', 'method', 'lambda'
    source: str
    operations: List[str]
    result_type: Optional[str]
    line_number: int


class CSharpLinqExtractor:
    """Extract and analyze LINQ patterns from C# code."""
    
    def __init__(self):
        # LINQ query syntax patterns
        self.query_pattern = re.compile(
            r'from\s+(\w+)\s+in\s+([^\s]+).*?select\s+([^;]+)',
            re.DOTALL | re.IGNORECASE
        )
        
        # LINQ method syntax patterns
        self.method_patterns = {
            'Where': re.compile(r'\.Where\s*\(([^)]+)\)', re.DOTALL),
            'Select': re.compile(r'\.Select\s*\(([^)]+)\)', re.DOTALL),
            'First': re.compile(r'\.First(?:OrDefault)?\s*\(([^)]*)\)', re.DOTALL),
            'Single': re.compile(r'\.Single(?:OrDefault)?\s*\(([^)]*)\)', re.DOTALL),
            'Any': re.compile(r'\.Any\s*\(([^)]*)\)', re.DOTALL),
            'All': re.compile(r'\.All\s*\(([^)]+)\)', re.DOTALL),
            'Count': re.compile(r'\.Count\s*\(([^)]*)\)', re.DOTALL),
            'OrderBy': re.compile(r'\.OrderBy(?:Descending)?\s*\(([^)]+)\)', re.DOTALL),
            'GroupBy': re.compile(r'\.GroupBy\s*\(([^)]+)\)', re.DOTALL),
            'Join': re.compile(r'\.Join\s*\(([^)]+)\)', re.DOTALL),
            'Take': re.compile(r'\.Take\s*\(([^)]+)\)', re.DOTALL),
            'Skip': re.compile(r'\.Skip\s*\(([^)]+)\)', re.DOTALL),
            'Distinct': re.compile(r'\.Distinct\s*\(\)', re.DOTALL),
            'ToList': re.compile(r'\.ToList\s*\(\)', re.DOTALL),
            'ToArray': re.compile(r'\.ToArray\s*\(\)', re.DOTALL),
        }
        
        # Lambda expression pattern
        self.lambda_pattern = re.compile(
            r'(\w+)\s*=>\s*([^,;)]+)',
            re.DOTALL
        )
    
    def extract_linq_expressions(
        self,
        cs_file: Path
    ) -> List[LinqExpression]:
        """
        Extract all LINQ expressions from a C# file.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            List of LinqExpression objects
        """
        if not cs_file.exists():
            return []
        
        content = cs_file.read_text(encoding='utf-8')
        expressions = []
        
        # Extract query syntax LINQ
        for match in self.query_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            
            expressions.append(LinqExpression(
                expression_type='query',
                source=match.group(2),
                operations=['from', 'select'],
                result_type=None,
                line_number=line_num
            ))
        
        # Extract method syntax LINQ
        method_linq = self._extract_method_linq(content)
        expressions.extend(method_linq)
        
        return expressions
    
    def _extract_method_linq(self, content: str) -> List[LinqExpression]:
        """Extract method-based LINQ expressions."""
        expressions = []
        
        # Find chains of LINQ methods
        # Pattern: collection.Where(...).Select(...).ToList()
        linq_chain_pattern = re.compile(
            r'(\w+)(?:\.(\w+)\s*\([^)]*\))+',
            re.DOTALL
        )
        
        for match in linq_chain_pattern.finditer(content):
            full_expr = match.group(0)
            source = match.group(1)
            
            # Detect if this is actually LINQ (has LINQ methods)
            operations = []
            for method_name, pattern in self.method_patterns.items():
                if pattern.search(full_expr):
                    operations.append(method_name)
            
            if operations:
                line_num = content[:match.start()].count('\n') + 1
                
                expressions.append(LinqExpression(
                    expression_type='method',
                    source=source,
                    operations=operations,
                    result_type=self._infer_result_type(operations),
                    line_number=line_num
                ))
        
        return expressions
    
    def _infer_result_type(self, operations: List[str]) -> Optional[str]:
        """Infer result type from LINQ operations."""
        if not operations:
            return None
        
        last_op = operations[-1]
        
        type_map = {
            'ToList': 'List',
            'ToArray': 'Array',
            'First': 'Single',
            'FirstOrDefault': 'Single',
            'Single': 'Single',
            'SingleOrDefault': 'Single',
            'Count': 'int',
            'Any': 'bool',
            'All': 'bool'
        }
        
        return type_map.get(last_op, 'IEnumerable')
    
    def extract_lambda_expressions(self, cs_file: Path) -> List[Dict]:
        """
        Extract lambda expressions from C# code.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            List of lambda expression dictionaries
        """
        if not cs_file.exists():
            return []
        
        content = cs_file.read_text(encoding='utf-8')
        lambdas = []
        
        for match in self.lambda_pattern.finditer(content):
            parameter = match.group(1)
            body = match.group(2).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            lambdas.append({
                'parameter': parameter,
                'body': body,
                'line': line_num,
                'is_expression': not body.startswith('{')
            })
        
        return lambdas
    
    def convert_linq_to_python(
        self,
        linq_expr: LinqExpression
    ) -> str:
        """
        Convert LINQ expression to Python equivalent.
        
        Args:
            linq_expr: LinqExpression object
            
        Returns:
            Python code string
        """
        python_code = linq_expr.source
        
        for operation in linq_expr.operations:
            if operation == 'Where':
                python_code = f"filter(lambda x: ..., {python_code})"
            elif operation == 'Select':
                python_code = f"map(lambda x: ..., {python_code})"
            elif operation in ('ToList', 'ToArray'):
                python_code = f"list({python_code})"
            elif operation == 'First':
                python_code = f"next(iter({python_code}))"
            elif operation == 'FirstOrDefault':
                python_code = f"next(iter({python_code}), None)"
            elif operation == 'Any':
                python_code = f"any({python_code})"
            elif operation == 'All':
                python_code = f"all({python_code})"
            elif operation == 'Count':
                python_code = f"len(list({python_code}))"
            elif operation == 'Distinct':
                python_code = f"set({python_code})"
            elif operation == 'OrderBy':
                python_code = f"sorted({python_code}, key=lambda x: ...)"
            elif operation == 'Take':
                python_code = f"itertools.islice({python_code}, n)"
            elif operation == 'Skip':
                python_code = f"itertools.islice({python_code}, n, None)"
        
        return python_code
    
    def has_complex_linq(self, cs_file: Path) -> bool:
        """
        Check if file contains complex LINQ patterns.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            True if complex LINQ is present
        """
        expressions = self.extract_linq_expressions(cs_file)
        
        # Complex if: multiple operations, join, group by
        for expr in expressions:
            if len(expr.operations) > 3:
                return True
            if any(op in expr.operations for op in ['Join', 'GroupBy']):
                return True
        
        return False
    
    def get_linq_summary(self, cs_file: Path) -> Dict[str, int]:
        """
        Get summary statistics for LINQ usage in a file.
        
        Args:
            cs_file: Path to C# file
            
        Returns:
            Dictionary with operation counts
        """
        expressions = self.extract_linq_expressions(cs_file)
        
        operation_counts = {}
        for expr in expressions:
            for op in expr.operations:
                operation_counts[op] = operation_counts.get(op, 0) + 1
        
        return {
            'total_expressions': len(expressions),
            'query_syntax': sum(1 for e in expressions if e.expression_type == 'query'),
            'method_syntax': sum(1 for e in expressions if e.expression_type == 'method'),
            'operations': operation_counts
        }
