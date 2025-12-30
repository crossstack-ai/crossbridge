"""
Regex patterns for parsing Cucumber/Gherkin feature files.

These patterns extract Features, Scenarios, Scenario Outlines, and Tags.
"""

# Feature declaration
FEATURE_PATTERN = r"^\s*Feature:\s*(.+)$"

# Scenario declarations
SCENARIO_PATTERN = r"^\s*Scenario:\s*(.+)$"
SCENARIO_OUTLINE_PATTERN = r"^\s*Scenario Outline:\s*(.+)$"

# Tags (can appear on same line, e.g., @tag1 @tag2)
TAG_PATTERN = r"@(\w+)"

# Background (not extracted as test, but tracked for context)
BACKGROUND_PATTERN = r"^\s*Background:\s*$"

# Examples table for Scenario Outline
EXAMPLES_PATTERN = r"^\s*Examples:\s*$"

# Comments (to be ignored)
COMMENT_PATTERN = r"^\s*#"

# Step keywords (for future step extraction)
GIVEN_PATTERN = r"^\s*Given\s+(.+)$"
WHEN_PATTERN = r"^\s*When\s+(.+)$"
THEN_PATTERN = r"^\s*Then\s+(.+)$"
AND_PATTERN = r"^\s*And\s+(.+)$"
BUT_PATTERN = r"^\s*But\s+(.+)$"
