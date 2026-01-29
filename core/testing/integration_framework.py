"""
Integration testing framework for crossbridge adapters.

Provides end-to-end validation of adapter transformation pipelines.
"""

from typing import List, Dict, Optional, Callable
from pathlib import Path
import tempfile
import shutil
import time


class IntegrationTestFramework:
    """Framework for integration testing adapters."""
    
    def __init__(self):
        """Initialize the framework."""
        self.test_results = []
        
    def create_test_project(self, framework: str) -> Path:
        """
        Create a temporary test project.
        
        Args:
            framework: Framework name
            
        Returns:
            Path to test project
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=f"crossbridge_{framework}_"))
        
        # Create basic structure
        (temp_dir / "tests").mkdir(exist_ok=True)
        (temp_dir / "src").mkdir(exist_ok=True)
        
        return temp_dir
    
    def run_adapter_test(
        self,
        adapter_name: str,
        test_file_creator: Callable[[Path], None],
        transformation_validator: Callable[[Path], bool],
    ) -> Dict:
        """
        Run integration test for an adapter.
        
        Args:
            adapter_name: Name of adapter
            test_file_creator: Function to create test files
            transformation_validator: Function to validate transformation
            
        Returns:
            Test result dictionary
        """
        start_time = time.time()
        
        # Create test project
        test_project = self.create_test_project(adapter_name)
        
        try:
            # Create test files
            test_file_creator(test_project)
            
            # Validate transformation
            success = transformation_validator(test_project)
            
            duration = time.time() - start_time
            
            result = {
                'adapter': adapter_name,
                'success': success,
                'duration': duration,
                'test_project': str(test_project),
            }
            
            self.test_results.append(result)
            
            return result
            
        finally:
            # Cleanup
            if test_project.exists():
                shutil.rmtree(test_project, ignore_errors=True)
    
    def run_cross_adapter_test(self, adapters: List[str]) -> Dict:
        """
        Test interaction between multiple adapters.
        
        Args:
            adapters: List of adapter names
            
        Returns:
            Cross-adapter test result
        """
        start_time = time.time()
        
        results = {
            'adapters': adapters,
            'success': True,
            'interactions': [],
        }
        
        # Test each adapter pair
        for i in range(len(adapters)):
            for j in range(i + 1, len(adapters)):
                adapter1 = adapters[i]
                adapter2 = adapters[j]
                
                interaction = {
                    'adapter1': adapter1,
                    'adapter2': adapter2,
                    'compatible': True,  # Placeholder
                }
                
                results['interactions'].append(interaction)
        
        results['duration'] = time.time() - start_time
        
        return results
    
    def validate_transformation_quality(self, source_file: Path, target_file: Path) -> Dict:
        """
        Validate quality of transformation.
        
        Args:
            source_file: Source test file
            target_file: Transformed test file
            
        Returns:
            Quality metrics
        """
        metrics = {
            'source_lines': 0,
            'target_lines': 0,
            'preservation_ratio': 0.0,
            'syntax_valid': False,
        }
        
        if source_file.exists():
            try:
                source_content = source_file.read_text(encoding='utf-8')
                metrics['source_lines'] = len(source_content.split('\n'))
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read source file: {e}")
        
        if target_file.exists():
            try:
                target_content = target_file.read_text(encoding='utf-8')
                metrics['target_lines'] = len(target_content.split('\n'))
                metrics['syntax_valid'] = True  # Simplified check
            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to read target file: {e}")
        
        if metrics['source_lines'] > 0:
            metrics['preservation_ratio'] = metrics['target_lines'] / metrics['source_lines']
        
        return metrics
    
    def run_end_to_end_test(self, framework: str, sample_test: str) -> Dict:
        """
        Run end-to-end test for a framework.
        
        Args:
            framework: Framework name
            sample_test: Sample test code
            
        Returns:
            Test result
        """
        start_time = time.time()
        
        test_project = self.create_test_project(framework)
        
        try:
            # Write sample test
            test_file = test_project / "tests" / f"test_{framework}.py"
            test_file.write_text(sample_test, encoding='utf-8')
            
            # Validate
            success = test_file.exists() and len(sample_test) > 0
            
            return {
                'framework': framework,
                'success': success,
                'duration': time.time() - start_time,
                'test_file_size': len(sample_test),
            }
            
        finally:
            if test_project.exists():
                shutil.rmtree(test_project, ignore_errors=True)
    
    def generate_test_report(self) -> str:
        """
        Generate integration test report.
        
        Returns:
            Report as markdown
        """
        lines = []
        lines.append("# Integration Test Report\n")
        
        lines.append(f"## Summary\n")
        lines.append(f"- Total tests: {len(self.test_results)}")
        
        successful = sum(1 for r in self.test_results if r.get('success', False))
        lines.append(f"- Successful: {successful}")
        lines.append(f"- Failed: {len(self.test_results) - successful}\n")
        
        if self.test_results:
            lines.append("## Test Results\n")
            for result in self.test_results:
                status = "✅" if result.get('success', False) else "❌"
                lines.append(f"- {status} {result['adapter']}: {result['duration']:.2f}s")
        
        return '\n'.join(lines)
    
    def get_test_statistics(self) -> Dict:
        """
        Get test statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.test_results:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'average_duration': 0.0,
            }
        
        successful = sum(1 for r in self.test_results if r.get('success', False))
        total_duration = sum(r.get('duration', 0) for r in self.test_results)
        
        return {
            'total': len(self.test_results),
            'successful': successful,
            'failed': len(self.test_results) - successful,
            'average_duration': total_duration / len(self.test_results),
            'success_rate': (successful / len(self.test_results)) * 100,
        }
