"""
Fix mock row objects to return tuples instead of MagicMock objects.
The repository functions use result[0], result[1] etc., not attributes.
"""

import re

def fix_discovery_repo_mocks():
    """Fix test_discovery_repo.py mocks."""
    filepath = 'tests/unit/persistence/test_discovery_repo.py'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the test_get_discovery_run_found test
    old_test = r'''    def test_get_discovery_run_found\(self, mock_session\):
        """Test retrieving an existing discovery run\."""
        mock_row = MagicMock\(\)
        mock_row\.id = 123
        mock_row\.project_name = "test-project"
        mock_row\.triggered_by = "cli"
        mock_row\.created_at = datetime\.now\(UTC\)
        mock_row\.git_commit = "abc123"
        mock_row\.git_branch = "main"
        mock_row\.metadata = \{"key": "value"\}
        
        mock_result = MagicMock\(\)
        mock_result\.fetchone\.return_value = mock_row
        mock_session\.execute\.return_value = mock_result
        
        discovery = get_discovery_run\(mock_session, uuid\.uuid4\(\)\)
        
        assert discovery is not None
        assert discovery\.id == 123
        assert discovery\.project_name == "test-project"
        assert discovery\.git_commit == "abc123"'''
    
    new_test = '''    def test_get_discovery_run_found(self, mock_session):
        """Test retrieving an existing discovery run."""
        test_uuid = uuid.uuid4()
        test_time = datetime.now(UTC)
        # Mock row as tuple matching SQL SELECT order: id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
        mock_row = (test_uuid, "test-project", "abc123", "main", "cli", test_time, {"key": "value"})
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_discovery_run(mock_session, test_uuid)
        
        assert discovery is not None
        assert discovery.id == test_uuid
        assert discovery.project_name == "test-project"
        assert discovery.git_commit == "abc123"'''
    
    content = re.sub(old_test, new_test, content, flags=re.DOTALL)
    
    # Fix test_get_latest_discovery_run_found similarly
    old_latest = r'''    def test_get_latest_discovery_run_found\(self, mock_session\):
        """Test retrieving the latest discovery run\."""
        mock_row = MagicMock\(\)
        mock_row\.id = 456
        mock_row\.project_name = "test-project"
        mock_row\.triggered_by = "ci"
        mock_row\.created_at = datetime\.now\(UTC\)
        mock_row\.git_commit = "xyz789"
        mock_row\.git_branch = "develop"
        mock_row\.metadata = \{\}
        
        mock_result = MagicMock\(\)
        mock_result\.fetchone\.return_value = mock_row
        mock_session\.execute\.return_value = mock_result
        
        discovery = get_latest_discovery_run\(mock_session, "test-project"\)
        
        assert discovery is not None
        assert discovery\.id == 456
        assert discovery\.project_name == "test-project"
        assert discovery\.git_commit == "xyz789"'''
    
    new_latest = '''    def test_get_latest_discovery_run_found(self, mock_session):
        """Test retrieving the latest discovery run."""
        test_uuid = uuid.uuid4()
        test_time = datetime.now(UTC)
        # Mock row as tuple matching SQL SELECT order
        mock_row = (test_uuid, "test-project", "xyz789", "develop", "ci", test_time, {})
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        discovery = get_latest_discovery_run(mock_session, "test-project")
        
        assert discovery is not None
        assert discovery.id == test_uuid
        assert discovery.project_name == "test-project"
        assert discovery.git_commit == "xyz789"'''
    
    content = re.sub(old_latest, new_latest, content, flags=re.DOTALL)
    
    # Fix test_list_discovery_runs_all
    old_list = r'''    def test_list_discovery_runs_all\(self, mock_session\):
        """Test listing all discovery runs\."""
        mock_row1 = MagicMock\(\)
        mock_row1\.id = 1
        mock_row1\.project_name = "project-a"
        mock_row1\.triggered_by = "cli"
        mock_row1\.created_at = datetime\.now\(UTC\)
        mock_row1\.git_commit = "abc"
        mock_row1\.git_branch = "main"
        mock_row1\.metadata = \{\}
        
        mock_row2 = MagicMock\(\)
        mock_row2\.id = 2
        mock_row2\.project_name = "project-b"
        mock_row2\.triggered_by = "ci"
        mock_row2\.created_at = datetime\.now\(UTC\)
        mock_row2\.git_commit = "def"
        mock_row2\.git_branch = "develop"
        mock_row2\.metadata = \{"key": "value"\}
        
        mock_result = MagicMock\(\)
        mock_result\.fetchall\.return_value = \[mock_row1, mock_row2\]
        mock_session\.execute\.return_value = mock_result
        
        discoveries = list_discovery_runs\(mock_session\)
        
        assert len\(discoveries\) == 2
        assert discoveries\[0\]\.id == 1
        assert discoveries\[1\]\.id == 2'''
    
    new_list = '''    def test_list_discovery_runs_all(self, mock_session):
        """Test listing all discovery runs."""
        test_uuid1 = uuid.uuid4()
        test_uuid2 = uuid.uuid4()
        test_time = datetime.now(UTC)
        # Mock rows as tuples
        mock_row1 = (test_uuid1, "project-a", "abc", "main", "cli", test_time, {})
        mock_row2 = (test_uuid2, "project-b", "def", "develop", "ci", test_time, {"key": "value"})
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result
        
        discoveries = list_discovery_runs(mock_session)
        
        assert len(discoveries) == 2
        assert discoveries[0].id == test_uuid1
        assert discoveries[1].id == test_uuid2'''
    
    content = re.sub(old_list, new_list, content, flags=re.DOTALL)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def main():
    fix_discovery_repo_mocks()
    print("\n✓ Mock rows fixed!")

if __name__ == "__main__":
    main()
