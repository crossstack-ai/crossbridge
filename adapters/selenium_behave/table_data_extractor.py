"""
Table data handling for Behave scenarios.

Handles multi-row table data in Given/When/Then steps.
"""

import re
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TableData:
    """Represents table data in a Behave step."""
    headers: List[str]
    rows: List[List[str]]
    step_keyword: str
    step_text: str
    line_number: int


class BehaveTableDataExtractor:
    """Extract and handle table data from Behave feature files."""
    
    def __init__(self):
        self.table_row_pattern = re.compile(
            r'^\s*\|(.+)\|$',
            re.MULTILINE
        )
        self.step_pattern = re.compile(
            r'^\s*(Given|When|Then|And|But)\s+(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
    
    def extract_tables_from_feature(
        self,
        feature_file: Path
    ) -> List[TableData]:
        """
        Extract all table data from a feature file.
        
        Args:
            feature_file: Path to .feature file
            
        Returns:
            List of TableData objects
        """
        if not feature_file.exists():
            return []
        
        content = feature_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        tables = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if line is a step
            step_match = self.step_pattern.match(line)
            if step_match:
                keyword = step_match.group(1)
                text = step_match.group(2).strip()
                
                # Check if next lines contain a table
                table_lines = []
                j = i + 1
                
                while j < len(lines):
                    if self.table_row_pattern.match(lines[j]):
                        table_lines.append(lines[j])
                        j += 1
                    elif lines[j].strip() == '':
                        j += 1
                        continue
                    else:
                        break
                
                if table_lines:
                    table_data = self._parse_table(table_lines)
                    if table_data:
                        tables.append(TableData(
                            headers=table_data['headers'],
                            rows=table_data['rows'],
                            step_keyword=keyword,
                            step_text=text,
                            line_number=i + 1
                        ))
                    i = j - 1
            
            i += 1
        
        return tables
    
    def _parse_table(self, table_lines: List[str]) -> Optional[Dict]:
        """Parse table lines into headers and rows."""
        if not table_lines:
            return None
        
        parsed_rows = []
        for line in table_lines:
            # Extract cell values
            match = self.table_row_pattern.match(line)
            if match:
                cells_str = match.group(1)
                cells = [cell.strip() for cell in cells_str.split('|')]
                parsed_rows.append(cells)
        
        if not parsed_rows:
            return None
        
        return {
            'headers': parsed_rows[0],
            'rows': parsed_rows[1:]
        }
    
    def convert_to_robot_arguments(
        self,
        table_data: TableData
    ) -> List[str]:
        """
        Convert Behave table to Robot Framework keyword arguments.
        
        Args:
            table_data: TableData object
            
        Returns:
            List of Robot keyword lines
        """
        keywords = []
        
        # Create a keyword for each row
        for row_idx, row in enumerate(table_data.rows):
            arg_dict = dict(zip(table_data.headers, row))
            
            # Convert to keyword call with arguments
            args_str = '    '.join(f'{k}={v}' for k, v in arg_dict.items())
            keywords.append(f"    Execute Step With Data    {args_str}")
        
        return keywords
    
    def convert_to_pytest_fixtures(
        self,
        table_data: TableData
    ) -> str:
        """
        Convert Behave table to pytest parametrize decorator.
        
        Args:
            table_data: TableData object
            
        Returns:
            Python pytest.mark.parametrize code
        """
        # Create parameter names
        params = ', '.join(table_data.headers)
        
        # Create parameter values
        values = []
        for row in table_data.rows:
            row_tuple = ', '.join(f'"{val}"' for val in row)
            values.append(f"    ({row_tuple})")
        
        values_str = ',\n'.join(values)
        
        return (
            f'@pytest.mark.parametrize(\n'
            f'    "{params}",\n'
            f'    [\n{values_str}\n    ]\n'
            f')\n'
        )
    
    def generate_data_dict(self, table_data: TableData) -> List[Dict[str, str]]:
        """
        Convert table to list of dictionaries.
        
        Args:
            table_data: TableData object
            
        Returns:
            List of dictionaries with table data
        """
        return [
            dict(zip(table_data.headers, row))
            for row in table_data.rows
        ]
    
    def has_table_data(self, feature_file: Path) -> bool:
        """Check if feature file contains table data."""
        tables = self.extract_tables_from_feature(feature_file)
        return len(tables) > 0
    
    def get_table_statistics(
        self,
        features_dir: Path
    ) -> Dict[str, int]:
        """
        Get statistics about table usage across feature files.
        
        Args:
            features_dir: Directory containing feature files
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_tables': 0,
            'total_rows': 0,
            'files_with_tables': 0,
            'avg_rows_per_table': 0
        }
        
        if not features_dir.exists():
            return stats
        
        all_tables = []
        files_with_tables = set()
        
        for feature_file in features_dir.rglob("*.feature"):
            tables = self.extract_tables_from_feature(feature_file)
            if tables:
                all_tables.extend(tables)
                files_with_tables.add(feature_file)
        
        stats['total_tables'] = len(all_tables)
        stats['files_with_tables'] = len(files_with_tables)
        stats['total_rows'] = sum(len(table.rows) for table in all_tables)
        
        if stats['total_tables'] > 0:
            stats['avg_rows_per_table'] = stats['total_rows'] / stats['total_tables']
        
        return stats
