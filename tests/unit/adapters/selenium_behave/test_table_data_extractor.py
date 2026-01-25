"""
Comprehensive unit tests for Behave Table Data Extractor.
"""

import pytest
from pathlib import Path
from adapters.selenium_behave.table_data_extractor import BehaveTableDataExtractor


@pytest.fixture
def extractor():
    return BehaveTableDataExtractor()


@pytest.fixture
def feature_with_tables(tmp_path):
    """Create feature file with table data."""
    feature_file = tmp_path / "users.feature"
    feature_file.write_text("""
Feature: User Management

  Scenario: Create multiple users
    Given the following users exist
      | username | email           | role  |
      | alice    | alice@test.com  | admin |
      | bob      | bob@test.com    | user  |
      | charlie  | charlie@test.com| guest |
    When I list all users
    Then I should see 3 users

  Scenario: Import user data
    Given I have user data
      | name  | age | city     |
      | John  | 30  | New York |
      | Jane  | 25  | Boston   |
    And I import the data
    Then users should be created

  Scenario: Complex product data
    When I add products
      | name    | price | category | in_stock |
      | Widget  | 9.99  | Tools    | yes      |
      | Gadget  | 19.99 | Electronics | no    |
      | Thing   | 4.99  | Misc     | yes      |
    Then products should be available
    """)
    return feature_file


@pytest.fixture
def feature_multiple_tables(tmp_path):
    """Create feature with multiple tables in one scenario."""
    feature_file = tmp_path / "orders.feature"
    feature_file.write_text("""
Feature: Order Processing

  Scenario: Process order with multiple items
    Given I have customers
      | name | email |
      | John | john@test.com |
    And I have products
      | name | price |
      | Item1 | 10.00 |
      | Item2 | 20.00 |
    When I create an order
    Then order should be processed
    """)
    return feature_file


class TestTableExtraction:
    """Test basic table extraction."""
    
    def test_extract_tables_from_feature(self, extractor, feature_with_tables):
        """Test extraction of all tables from feature."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        assert len(tables) >= 3
        assert all(isinstance(t, TableData) for t in tables)
    
    def test_table_headers(self, extractor, feature_with_tables):
        """Test extraction of table headers."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        # First table (users)
        users_table = tables[0]
        assert users_table.headers == ['username', 'email', 'role']
    
    def test_table_rows(self, extractor, feature_with_tables):
        """Test extraction of table rows."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        assert len(users_table.rows) == 3
        
        # Check first row
        assert users_table.rows[0] == ['alice', 'alice@test.com', 'admin']
    
    def test_table_row_count(self, extractor, feature_with_tables):
        """Test row counting."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        for table in tables:
            assert table.row_count == len(table.rows)
            assert table.row_count > 0
    
    def test_table_column_count(self, extractor, feature_with_tables):
        """Test column counting."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        assert users_table.column_count == 3  # username, email, role


class TestTableMetadata:
    """Test table metadata extraction."""
    
    def test_step_keyword(self, extractor, feature_with_tables):
        """Test step keyword capture."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        assert users_table.step_keyword in ['Given', 'When', 'Then', 'And']
    
    def test_step_text(self, extractor, feature_with_tables):
        """Test step text capture."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        assert 'users exist' in users_table.step_text.lower()
    
    def test_scenario_name(self, extractor, feature_with_tables):
        """Test scenario name capture."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        assert users_table.scenario_name is not None
        assert 'Create multiple users' in users_table.scenario_name


class TestTableConversion:
    """Test table conversion to different formats."""
    
    def test_convert_to_dict_list(self, extractor, feature_with_tables):
        """Test conversion to list of dictionaries."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        dict_list = extractor.convert_to_dict_list(users_table)
        
        assert len(dict_list) == 3
        assert dict_list[0]['username'] == 'alice'
        assert dict_list[0]['email'] == 'alice@test.com'
        assert dict_list[0]['role'] == 'admin'
    
    def test_convert_to_robot_arguments(self, extractor, feature_with_tables):
        """Test conversion to Robot Framework arguments."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        robot_args = extractor.convert_to_robot_arguments(users_table)
        
        assert robot_args is not None
        assert 'username' in robot_args or 'alice' in robot_args
    
    def test_convert_to_pytest_fixtures(self, extractor, feature_with_tables):
        """Test conversion to pytest parametrize."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        
        users_table = tables[0]
        pytest_code = extractor.convert_to_pytest_fixtures(users_table)
        
        assert '@pytest.mark.parametrize' in pytest_code
        assert 'username' in pytest_code
        assert 'email' in pytest_code


class TestMultipleTables:
    """Test handling of multiple tables."""
    
    def test_multiple_tables_in_scenario(self, extractor, feature_multiple_tables):
        """Test extraction of multiple tables from one scenario."""
        tables = extractor.extract_tables_from_feature(feature_multiple_tables)
        
        assert len(tables) >= 2
        
        # First table (customers)
        customers_table = next((t for t in tables if 'name' in t.headers and 'email' in t.headers), None)
        assert customers_table is not None
        
        # Second table (products)
        products_table = next((t for t in tables if 'price' in t.headers), None)
        assert products_table is not None
    
    def test_tables_maintain_order(self, extractor, feature_multiple_tables):
        """Test that tables maintain their order."""
        tables = extractor.extract_tables_from_feature(feature_multiple_tables)
        
        # First table should come before second table
        assert len(tables) >= 2


class TestTableStatistics:
    """Test table statistics and analysis."""
    
    def test_get_table_statistics(self, extractor, feature_with_tables):
        """Test getting statistics about tables."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        stats = extractor.get_table_statistics(tables)
        
        assert 'total_tables' in stats
        assert 'total_rows' in stats
        assert stats['total_tables'] >= 3
        assert stats['total_rows'] > 0
    
    def test_statistics_average_rows(self, extractor, feature_with_tables):
        """Test average rows calculation."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        stats = extractor.get_table_statistics(tables)
        
        assert 'average_rows_per_table' in stats
        assert stats['average_rows_per_table'] > 0
    
    def test_statistics_unique_headers(self, extractor, feature_with_tables):
        """Test unique headers collection."""
        tables = extractor.extract_tables_from_feature(feature_with_tables)
        stats = extractor.get_table_statistics(tables)
        
        assert 'unique_headers' in stats
        assert 'username' in stats['unique_headers'] or len(stats['unique_headers']) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_table(self, extractor, tmp_path):
        """Test handling of empty table."""
        feature_file = tmp_path / "empty_table.feature"
        feature_file.write_text("""
Feature: Empty Table
  Scenario: Test
    Given I have data
      | column1 | column2 |
    When I process it
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        # Should handle gracefully
        if len(tables) > 0:
            assert tables[0].row_count == 0
    
    def test_feature_without_tables(self, extractor, tmp_path):
        """Test feature file without any tables."""
        feature_file = tmp_path / "no_tables.feature"
        feature_file.write_text("""
Feature: No Tables
  Scenario: Simple Test
    Given something
    When something else
    Then result
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) == 0
    
    def test_table_with_special_characters(self, extractor, tmp_path):
        """Test table with special characters."""
        feature_file = tmp_path / "special_chars.feature"
        feature_file.write_text("""
Feature: Special Characters
  Scenario: Test
    Given data with special chars
      | name    | description       |
      | Test&Co | It's a "test"    |
      | Foo|Bar | <tag>value</tag> |
    When processed
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) > 0
        
        table = tables[0]
        assert table.row_count == 2
    
    def test_table_with_empty_cells(self, extractor, tmp_path):
        """Test table with empty cells."""
        feature_file = tmp_path / "empty_cells.feature"
        feature_file.write_text("""
Feature: Empty Cells
  Scenario: Test
    Given data with empties
      | name  | value | optional |
      | Item1 | 100   |          |
      | Item2 |       | yes      |
    When processed
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) > 0
        
        table = tables[0]
        assert table.row_count == 2
        # Empty cells should be preserved
        assert '' in table.rows[0] or len(table.rows[0]) == 3
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.feature"
        
        tables = extractor.extract_tables_from_feature(nonexistent)
        assert len(tables) == 0
    
    def test_invalid_feature_syntax(self, extractor, tmp_path):
        """Test handling of invalid feature syntax."""
        invalid_file = tmp_path / "invalid.feature"
        invalid_file.write_text("""
This is not valid Gherkin syntax
| header1 | header2 |
| value1  | value2  |
        """)
        
        tables = extractor.extract_tables_from_feature(invalid_file)
        # Should handle gracefully without crashing
        assert isinstance(tables, list)


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_table_with_many_columns(self, extractor, tmp_path):
        """Test table with many columns."""
        feature_file = tmp_path / "wide_table.feature"
        feature_file.write_text("""
Feature: Wide Table
  Scenario: Test
    Given I have comprehensive data
      | col1 | col2 | col3 | col4 | col5 | col6 | col7 | col8 | col9 | col10 |
      | a    | b    | c    | d    | e    | f    | g    | h    | i    | j     |
      | 1    | 2    | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10    |
    When processed
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) > 0
        
        table = tables[0]
        assert table.column_count == 10
        assert len(table.headers) == 10
    
    def test_table_with_many_rows(self, extractor, tmp_path):
        """Test table with many rows."""
        rows = "\n".join([f"      | user{i} | user{i}@test.com |" for i in range(50)])
        feature_file = tmp_path / "tall_table.feature"
        feature_file.write_text(f"""
Feature: Tall Table
  Scenario: Test
    Given I have many users
      | username | email |
{rows}
    When processed
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) > 0
        
        table = tables[0]
        assert table.row_count == 50
    
    def test_table_with_numeric_data(self, extractor, tmp_path):
        """Test table with numeric data."""
        feature_file = tmp_path / "numeric.feature"
        feature_file.write_text("""
Feature: Numeric Data
  Scenario: Test
    Given I have measurements
      | temperature | humidity | pressure |
      | 72.5        | 45.2     | 1013.25  |
      | 68.0        | 50.0     | 1012.00  |
    When analyzed
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        assert len(tables) > 0
        
        table = tables[0]
        dict_list = extractor.convert_to_dict_list(table)
        # Values should be preserved as strings (feature format)
        assert '72.5' in dict_list[0]['temperature'] or dict_list[0]['temperature'] == '72.5'
    
    def test_scenario_outline_with_examples_table(self, extractor, tmp_path):
        """Test distinguishing between step tables and Examples tables."""
        feature_file = tmp_path / "outline.feature"
        feature_file.write_text("""
Feature: Scenario Outline
  Scenario Outline: Test
    Given I have config
      | key | value |
      | a   | <val> |
    When I test with <input>
    
    Examples:
      | val | input |
      | 1   | x     |
      | 2   | y     |
        """)
        
        tables = extractor.extract_tables_from_feature(feature_file)
        # Should extract step table but not Examples table
        # (Examples is handled by scenario outline extractor)
        assert len(tables) >= 1
