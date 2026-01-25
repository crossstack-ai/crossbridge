"""
Complex TestNG DataProvider extraction with external data sources.

Handles @DataProvider methods with Excel, CSV, JSON, and database sources.
"""

import re
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DataProviderInfo:
    """Information about a TestNG DataProvider."""
    name: str
    method_name: str
    return_type: str
    data_source: str  # 'inline', 'excel', 'csv', 'json', 'database', 'method'
    source_file: Optional[str]
    parameters: List[str]
    is_parallel: bool
    line_number: int


class TestNGDataProviderExtractor:
    """Extract complex DataProvider patterns from TestNG tests."""
    
    def __init__(self):
        # DataProvider annotation pattern
        self.dataprovider_pattern = re.compile(
            r'@DataProvider\s*(?:\(\s*name\s*=\s*"([^"]+)"(?:\s*,\s*parallel\s*=\s*(true|false))?\s*\))?\s*'
            r'public\s+(?:static\s+)?(?:Object\[\]\[\]|Iterator<Object\[\]>)\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE | re.DOTALL
        )
        
        # Test method with DataProvider
        self.test_dataprovider_pattern = re.compile(
            r'@Test\s*\(\s*dataProvider\s*=\s*"([^"]+)"\s*\)',
            re.MULTILINE
        )
        
        # External data source patterns
        self.excel_pattern = re.compile(
            r'ExcelUtils?\.(?:read|get|load)\w*\("([^"]+)"',
            re.IGNORECASE
        )
        self.csv_pattern = re.compile(
            r'CSVReader|Files\.readAllLines\([^)]*"([^"]+\.csv)"',
            re.IGNORECASE
        )
        self.json_pattern = re.compile(
            r'(?:Gson|Jackson|JSON).*?(?:parse|read)\w*\("([^"]+\.json)"',
            re.IGNORECASE | re.DOTALL
        )
        self.db_pattern = re.compile(
            r'(?:Connection|ResultSet|PreparedStatement|executeQuery)',
            re.IGNORECASE
        )
    
    def extract_dataproviders(
        self,
        java_file: Path
    ) -> List[DataProviderInfo]:
        """
        Extract all DataProvider methods from a Java test file.
        
        Args:
            java_file: Path to Java test file
            
        Returns:
            List of DataProviderInfo objects
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        dataproviders = []
        
        for match in self.dataprovider_pattern.finditer(content):
            provider_name = match.group(1) if match.group(1) else match.group(3)
            is_parallel = match.group(2) == 'true' if match.group(2) else False
            method_name = match.group(3)
            line_num = content[:match.start()].count('\n') + 1
            
            # Extract method body
            method_start = match.end()
            method_body = self._extract_method_body(content, method_start)
            
            # Detect data source type
            data_source, source_file = self._detect_data_source(method_body)
            
            # Extract parameters
            parameters = self._extract_parameters(method_body)
            
            dataproviders.append(DataProviderInfo(
                name=provider_name,
                method_name=method_name,
                return_type='Object[][]',
                data_source=data_source,
                source_file=source_file,
                parameters=parameters,
                is_parallel=is_parallel,
                line_number=line_num
            ))
        
        return dataproviders
    
    def _extract_method_body(self, content: str, start_pos: int) -> str:
        """Extract method body starting from position."""
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
    
    def _detect_data_source(
        self,
        method_body: str
    ) -> Tuple[str, Optional[str]]:
        """Detect the type of data source used in DataProvider."""
        # Check for Excel
        excel_match = self.excel_pattern.search(method_body)
        if excel_match:
            return 'excel', excel_match.group(1)
        
        # Check for CSV
        csv_match = self.csv_pattern.search(method_body)
        if csv_match:
            return 'csv', csv_match.group(1)
        
        # Check for JSON
        json_match = self.json_pattern.search(method_body)
        if json_match:
            return 'json', json_match.group(1)
        
        # Check for database
        if self.db_pattern.search(method_body):
            return 'database', None
        
        # Check for inline data (return new Object[][] {...})
        if 'return new Object[][]' in method_body:
            return 'inline', None
        
        # Check for method call (delegates to another method)
        if re.search(r'return\s+\w+\s*\(', method_body):
            return 'method', None
        
        return 'unknown', None
    
    def _extract_parameters(self, method_body: str) -> List[str]:
        """Extract parameter names from data provider."""
        # Look for variable names in Object[][] array
        param_pattern = re.compile(
            r'new\s+Object\[\]\s*\{\s*([^}]+)\s*\}',
            re.DOTALL
        )
        
        parameters = []
        for match in param_pattern.finditer(method_body):
            param_str = match.group(1)
            # Extract individual parameters
            params = re.findall(r'"([^"]+)"|\b(\w+)\b', param_str)
            for param_tuple in params:
                param = param_tuple[0] or param_tuple[1]
                if param and param not in ['new', 'Object', 'String']:
                    parameters.append(param)
        
        return parameters[:10]  # Limit to first 10
    
    def find_tests_using_dataprovider(
        self,
        java_file: Path,
        provider_name: str
    ) -> List[str]:
        """
        Find test methods that use a specific DataProvider.
        
        Args:
            java_file: Path to Java file
            provider_name: Name of DataProvider
            
        Returns:
            List of test method names
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        test_methods = []
        
        # Pattern: @Test(dataProvider = "providerName") followed by method
        pattern = re.compile(
            rf'@Test\s*\(\s*dataProvider\s*=\s*"{provider_name}"\s*\)\s*'
            r'public\s+void\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
        
        for match in pattern.finditer(content):
            test_method = match.group(1)
            test_methods.append(test_method)
        
        return test_methods
    
    def extract_excel_config(
        self,
        method_body: str
    ) -> Optional[Dict[str, any]]:
        """Extract Excel file configuration from DataProvider."""
        excel_match = self.excel_pattern.search(method_body)
        if not excel_match:
            return None
        
        file_path = excel_match.group(1)
        
        # Try to extract sheet name
        sheet_pattern = re.compile(r'getSheet\w*\("([^"]+)"')
        sheet_match = sheet_pattern.search(method_body)
        sheet_name = sheet_match.group(1) if sheet_match else 'Sheet1'
        
        # Try to extract row/column info
        row_pattern = re.compile(r'startRow["\s]*[=:]\s*(\d+)')
        row_match = row_pattern.search(method_body)
        start_row = int(row_match.group(1)) if row_match else 0
        
        return {
            'file': file_path,
            'sheet': sheet_name,
            'start_row': start_row,
            'format': 'xlsx' if '.xlsx' in file_path else 'xls'
        }
    
    def convert_to_pytest_parametrize(
        self,
        dataprovider: DataProviderInfo
    ) -> str:
        """
        Convert TestNG DataProvider to pytest @pytest.mark.parametrize.
        
        Args:
            dataprovider: DataProviderInfo object
            
        Returns:
            Python pytest.mark.parametrize code
        """
        if dataprovider.data_source == 'inline':
            # Simple inline parametrization
            return (
                f"@pytest.mark.parametrize('{', '.join(dataprovider.parameters)}', [\n"
                f"    # Add test data here\n"
                f"    (value1, value2, ...),\n"
                f"])\n"
            )
        
        elif dataprovider.data_source == 'excel':
            # Excel data source
            return (
                f"# Install: pip install openpyxl pandas\n"
                f"import pandas as pd\n\n"
                f"def load_excel_data():\n"
                f"    df = pd.read_excel('{dataprovider.source_file}')\n"
                f"    return df.values.tolist()\n\n"
                f"@pytest.mark.parametrize('{', '.join(dataprovider.parameters)}', "
                f"load_excel_data())\n"
            )
        
        elif dataprovider.data_source == 'csv':
            # CSV data source
            return (
                f"import csv\n\n"
                f"def load_csv_data():\n"
                f"    with open('{dataprovider.source_file}') as f:\n"
                f"        return list(csv.reader(f))\n\n"
                f"@pytest.mark.parametrize('{', '.join(dataprovider.parameters)}', "
                f"load_csv_data())\n"
            )
        
        elif dataprovider.data_source == 'json':
            # JSON data source
            return (
                f"import json\n\n"
                f"def load_json_data():\n"
                f"    with open('{dataprovider.source_file}') as f:\n"
                f"        data = json.load(f)\n"
                f"        return [tuple(d.values()) for d in data]\n\n"
                f"@pytest.mark.parametrize('{', '.join(dataprovider.parameters)}', "
                f"load_json_data())\n"
            )
        
        else:
            return f"# DataProvider '{dataprovider.name}' - custom implementation needed"
    
    def has_external_dataprovider(self, java_file: Path) -> bool:
        """Check if file has DataProviders with external data sources."""
        dataproviders = self.extract_dataproviders(java_file)
        return any(
            dp.data_source in ['excel', 'csv', 'json', 'database']
            for dp in dataproviders
        )
    
    def get_dataprovider_summary(
        self,
        project_root: Path
    ) -> Dict[str, int]:
        """
        Get summary of DataProvider usage across project.
        
        Args:
            project_root: Root directory of project
            
        Returns:
            Dictionary with usage statistics
        """
        summary = {
            'total_providers': 0,
            'inline': 0,
            'excel': 0,
            'csv': 0,
            'json': 0,
            'database': 0,
            'parallel': 0
        }
        
        for java_file in project_root.rglob("*Test*.java"):
            providers = self.extract_dataproviders(java_file)
            summary['total_providers'] += len(providers)
            
            for provider in providers:
                summary[provider.data_source] = summary.get(provider.data_source, 0) + 1
                if provider.is_parallel:
                    summary['parallel'] += 1
        
        return summary
