"""
Unit tests for Cucumber JSON parser.

Tests cover:
- Basic parsing of features, scenarios, and steps
- Status computation logic
- Tag handling
- Error handling
- Multiple report parsing
"""

import json
import pytest
from pathlib import Path
from adapters.selenium_bdd_java.cucumber_json_parser import (
    parse_cucumber_json,
    parse_multiple_cucumber_reports,
    CucumberJsonParseError
)
from adapters.selenium_bdd_java.models import FeatureResult, ScenarioResult, StepResult


# Sample Cucumber JSON data
SIMPLE_PASSING_REPORT = [
    {
        "uri": "features/login.feature",
        "name": "Login Feature",
        "tags": [{"name": "@smoke"}],
        "elements": [
            {
                "type": "scenario",
                "name": "Valid login",
                "line": 10,
                "tags": [{"name": "@critical"}],
                "steps": [
                    {
                        "keyword": "Given ",
                        "name": "user is on login page",
                        "result": {
                            "status": "passed",
                            "duration": 100000000
                        }
                    },
                    {
                        "keyword": "When ",
                        "name": "user enters valid credentials",
                        "result": {
                            "status": "passed",
                            "duration": 120000000
                        }
                    },
                    {
                        "keyword": "Then ",
                        "name": "user is logged in successfully",
                        "result": {
                            "status": "passed",
                            "duration": 80000000
                        }
                    }
                ]
            }
        ]
    }
]


FAILING_REPORT = [
    {
        "uri": "features/checkout.feature",
        "name": "Checkout Feature",
        "elements": [
            {
                "type": "scenario",
                "name": "Add item to cart",
                "line": 15,
                "steps": [
                    {
                        "keyword": "Given ",
                        "name": "user has items in cart",
                        "result": {
                            "status": "passed",
                            "duration": 50000000
                        }
                    },
                    {
                        "keyword": "When ",
                        "name": "user proceeds to checkout",
                        "result": {
                            "status": "failed",
                            "duration": 30000000,
                            "error_message": "Payment gateway timeout"
                        }
                    },
                    {
                        "keyword": "Then ",
                        "name": "order is placed",
                        "result": {
                            "status": "skipped",
                            "duration": 0
                        }
                    }
                ]
            }
        ]
    }
]


SCENARIO_OUTLINE_REPORT = [
    {
        "uri": "features/search.feature",
        "name": "Search Feature",
        "elements": [
            {
                "type": "scenario_outline",
                "name": "Search for products",
                "line": 20,
                "tags": [{"name": "@regression"}],
                "steps": [
                    {
                        "keyword": "When ",
                        "name": "user searches for 'laptop'",
                        "result": {
                            "status": "passed",
                            "duration": 200000000
                        }
                    }
                ]
            }
        ]
    }
]


MIXED_STATUS_REPORT = [
    {
        "uri": "features/mixed.feature",
        "name": "Mixed Status Feature",
        "elements": [
            {
                "type": "scenario",
                "name": "Passing scenario",
                "line": 5,
                "steps": [
                    {
                        "keyword": "Given ",
                        "name": "step passes",
                        "result": {"status": "passed", "duration": 1000000}
                    }
                ]
            },
            {
                "type": "scenario",
                "name": "Failing scenario",
                "line": 10,
                "steps": [
                    {
                        "keyword": "Given ",
                        "name": "step fails",
                        "result": {
                            "status": "failed",
                            "duration": 2000000,
                            "error_message": "Assertion failed"
                        }
                    }
                ]
            },
            {
                "type": "scenario",
                "name": "Skipped scenario",
                "line": 15,
                "steps": [
                    {
                        "keyword": "Given ",
                        "name": "step skipped",
                        "result": {"status": "skipped", "duration": 0}
                    }
                ]
            }
        ]
    }
]


class TestCucumberJsonParser:
    """Test suite for Cucumber JSON parser."""
    
    def test_parse_simple_passing_report(self, tmp_path):
        """Test parsing a simple passing report."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(SIMPLE_PASSING_REPORT))
        
        features = parse_cucumber_json(report)
        
        assert len(features) == 1
        assert features[0].name == "Login Feature"
        assert features[0].uri == "features/login.feature"
        assert "@smoke" in features[0].tags
        
        assert len(features[0].scenarios) == 1
        scenario = features[0].scenarios[0]
        assert scenario.scenario == "Valid login"
        assert scenario.status == "passed"
        assert scenario.line == 10
        assert "@smoke" in scenario.tags
        assert "@critical" in scenario.tags
        
        assert len(scenario.steps) == 3
        assert all(step.status == "passed" for step in scenario.steps)
        assert scenario.steps[0].name == "Given user is on login page"
        assert scenario.steps[1].duration_ns == 120000000
    
    def test_parse_failing_report(self, tmp_path):
        """Test parsing a report with failed steps."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(FAILING_REPORT))
        
        features = parse_cucumber_json(report)
        
        assert len(features) == 1
        scenario = features[0].scenarios[0]
        
        # Scenario should be marked as failed
        assert scenario.status == "failed"
        
        # Check individual step statuses
        assert scenario.steps[0].status == "passed"
        assert scenario.steps[1].status == "failed"
        assert scenario.steps[1].error_message == "Payment gateway timeout"
        assert scenario.steps[2].status == "skipped"
        
        # Check failed steps property
        assert len(scenario.failed_steps) == 1
        assert scenario.failed_steps[0].name == "When user proceeds to checkout"
    
    def test_scenario_outline_parsing(self, tmp_path):
        """Test parsing scenario outlines."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(SCENARIO_OUTLINE_REPORT))
        
        features = parse_cucumber_json(report)
        
        scenario = features[0].scenarios[0]
        assert scenario.scenario_type == "scenario_outline"
        assert scenario.scenario == "Search for products"
        assert "@regression" in scenario.tags
    
    def test_scenario_status_computation(self, tmp_path):
        """Test scenario status is computed correctly from step statuses."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(MIXED_STATUS_REPORT))
        
        features = parse_cucumber_json(report)
        scenarios = features[0].scenarios
        
        # Test status computation rules
        assert scenarios[0].status == "passed"  # All passed
        assert scenarios[1].status == "failed"  # Has failed step
        assert scenarios[2].status == "skipped"  # All skipped
    
    def test_feature_statistics(self, tmp_path):
        """Test feature-level statistics calculation."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(MIXED_STATUS_REPORT))
        
        features = parse_cucumber_json(report)
        feature = features[0]
        
        assert feature.total_scenarios == 3
        assert feature.passed_scenarios == 1
        assert feature.failed_scenarios == 1
        assert feature.skipped_scenarios == 1
        assert feature.overall_status == "failed"  # Has at least one failure
    
    def test_scenario_duration_calculation(self, tmp_path):
        """Test total duration calculation for scenarios."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(SIMPLE_PASSING_REPORT))
        
        features = parse_cucumber_json(report)
        scenario = features[0].scenarios[0]
        
        # Total duration should be sum of all steps
        expected_duration = 100000000 + 120000000 + 80000000
        assert scenario.total_duration_ns == expected_duration
    
    def test_file_not_found_error(self, tmp_path):
        """Test error handling for non-existent file."""
        non_existent = tmp_path / "does-not-exist.json"
        
        with pytest.raises(FileNotFoundError):
            parse_cucumber_json(non_existent)
    
    def test_invalid_json_error(self, tmp_path):
        """Test error handling for invalid JSON."""
        report = tmp_path / "invalid.json"
        report.write_text("{ this is not valid json }")
        
        with pytest.raises(CucumberJsonParseError):
            parse_cucumber_json(report)
    
    def test_invalid_json_structure_error(self, tmp_path):
        """Test error handling for JSON with wrong structure."""
        report = tmp_path / "wrong-structure.json"
        report.write_text('{"not": "a list"}')
        
        with pytest.raises(CucumberJsonParseError):
            parse_cucumber_json(report)
    
    def test_tag_normalization(self, tmp_path):
        """Test that tags are normalized with @ prefix."""
        data = [
            {
                "uri": "features/test.feature",
                "name": "Test Feature",
                "tags": [{"name": "smoke"}, {"name": "@regression"}],
                "elements": []
            }
        ]
        
        report = tmp_path / "report.json"
        report.write_text(json.dumps(data))
        
        features = parse_cucumber_json(report)
        
        # Both tags should have @ prefix
        assert "@smoke" in features[0].tags
        assert "@regression" in features[0].tags
    
    def test_missing_optional_fields(self, tmp_path):
        """Test parsing with missing optional fields."""
        data = [
            {
                "uri": "features/test.feature",
                "elements": [
                    {
                        "type": "scenario",
                        "steps": [
                            {
                                "result": {"status": "passed"}
                            }
                        ]
                    }
                ]
            }
        ]
        
        report = tmp_path / "report.json"
        report.write_text(json.dumps(data))
        
        features = parse_cucumber_json(report)
        
        # Should use defaults for missing fields
        assert features[0].name == "Unnamed Feature"
        assert features[0].scenarios[0].scenario == "Unnamed Scenario"
        assert features[0].scenarios[0].line == -1
    
    def test_parse_multiple_reports(self, tmp_path):
        """Test parsing multiple reports."""
        report1 = tmp_path / "report1.json"
        report1.write_text(json.dumps(SIMPLE_PASSING_REPORT))
        
        report2 = tmp_path / "report2.json"
        report2.write_text(json.dumps(FAILING_REPORT))
        
        features = parse_multiple_cucumber_reports([report1, report2])
        
        assert len(features) == 2
        assert features[0].name == "Login Feature"
        assert features[1].name == "Checkout Feature"
    
    def test_parse_multiple_reports_with_missing_file(self, tmp_path):
        """Test that missing files are skipped when parsing multiple reports."""
        report1 = tmp_path / "report1.json"
        report1.write_text(json.dumps(SIMPLE_PASSING_REPORT))
        
        non_existent = tmp_path / "does-not-exist.json"
        
        # Should not raise error, just skip missing file
        features = parse_multiple_cucumber_reports([report1, non_existent])
        
        assert len(features) == 1
        assert features[0].name == "Login Feature"
    
    def test_step_with_keyword(self, tmp_path):
        """Test that step names include keywords."""
        report = tmp_path / "report.json"
        report.write_text(json.dumps(SIMPLE_PASSING_REPORT))
        
        features = parse_cucumber_json(report)
        steps = features[0].scenarios[0].steps
        
        # Step names should include keywords (Given, When, Then)
        assert steps[0].name.startswith("Given")
        assert steps[1].name.startswith("When")
        assert steps[2].name.startswith("Then")
    
    def test_undefined_step_status(self, tmp_path):
        """Test handling of undefined steps."""
        data = [
            {
                "uri": "features/test.feature",
                "name": "Test Feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Test Scenario",
                        "line": 5,
                        "steps": [
                            {
                                "keyword": "Given ",
                                "name": "undefined step",
                                "result": {
                                    "status": "undefined",
                                    "duration": 0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        
        report = tmp_path / "report.json"
        report.write_text(json.dumps(data))
        
        features = parse_cucumber_json(report)
        scenario = features[0].scenarios[0]
        
        # Scenario with undefined steps should be marked as skipped
        assert scenario.status == "skipped"
        assert scenario.steps[0].status == "undefined"
    
    def test_pending_step_status(self, tmp_path):
        """Test handling of pending steps."""
        data = [
            {
                "uri": "features/test.feature",
                "name": "Test Feature",
                "elements": [
                    {
                        "type": "scenario",
                        "name": "Test Scenario",
                        "line": 5,
                        "steps": [
                            {
                                "keyword": "Given ",
                                "name": "pending step",
                                "result": {
                                    "status": "pending",
                                    "duration": 0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        
        report = tmp_path / "report.json"
        report.write_text(json.dumps(data))
        
        features = parse_cucumber_json(report)
        scenario = features[0].scenarios[0]
        
        # Scenario with pending steps should be marked as skipped
        assert scenario.status == "skipped"
        assert scenario.steps[0].status == "pending"


class TestModels:
    """Test suite for domain models."""
    
    def test_step_result_validation(self):
        """Test StepResult status validation."""
        # Valid status should work
        step = StepResult(
            name="test step",
            status="passed",
            duration_ns=1000
        )
        assert step.status == "passed"
        
        # Invalid status should raise error
        with pytest.raises(ValueError):
            StepResult(
                name="test step",
                status="invalid",
                duration_ns=1000
            )
    
    def test_scenario_result_validation(self):
        """Test ScenarioResult type validation."""
        # Valid scenario type
        scenario = ScenarioResult(
            feature="Test Feature",
            scenario="Test Scenario",
            scenario_type="scenario",
            tags=[],
            steps=[],
            status="passed",
            uri="test.feature",
            line=1
        )
        assert scenario.scenario_type == "scenario"
        
        # Invalid scenario type should raise error
        with pytest.raises(ValueError):
            ScenarioResult(
                feature="Test Feature",
                scenario="Test Scenario",
                scenario_type="invalid",
                tags=[],
                steps=[],
                status="passed",
                uri="test.feature",
                line=1
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
