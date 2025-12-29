"""
Selenium-Java test metadata extractor.

This extractor parses Java Selenium test files to extract test metadata
without executing them. Useful for impact analysis and test selection.
"""

from pathlib import Path
from typing import List
import re

from ..common.extractor import BaseTestExtractor
from ..common.models import TestMetadata
from .config import SeleniumJavaConfig
from .patterns import TEST_ANNOTATIONS, TAG_ANNOTATIONS, METHOD_PATTERN, CLASS_PATTERN


class SeleniumJavaExtractor(BaseTestExtractor):

    def __init__(self, config: SeleniumJavaConfig):
        self.config = config

    def extract_tests(self) -> List[TestMetadata]:
        results = []

        for java_file in Path(self.config.root_dir).rglob("*.java"):
            content = java_file.read_text(encoding="utf-8", errors="ignore")

            class_match = re.search(CLASS_PATTERN, content)
            if not class_match:
                continue

            class_name = class_match.group(1)

            for method in self._extract_test_methods(content):
                tags = self._extract_tags(content)

                results.append(
                    TestMetadata(
                        framework=f"selenium-java-{self.config.test_framework}",
                        test_name=f"{class_name}.{method}",
                        file_path=str(java_file),
                        tags=tags,
                        test_type="ui",
                        language="java"
                    )
                )

        return results

    def _extract_test_methods(self, content: str) -> List[str]:
        methods = []

        # Pattern for both JUnit 4 (public void) and JUnit 5 (void without public)
        # Also handles TestNG (public void)
        test_blocks = re.finditer(
            r"@Test[\s\S]*?(?:public\s+)?void\s+(\w+)\s*\(",
            content
        )

        for match in test_blocks:
            methods.append(match.group(1))

        return methods

    def _extract_tags(self, content: str) -> List[str]:
        tags = []

        for match in re.findall(r"@Tag\(\"(.*?)\"\)", content):
            tags.append(match)

        for match in re.findall(r"@Groups?\(\{?(.*?)\}?\)", content):
            tags.extend([t.strip().strip('"') for t in match.split(",")])

        return list(set(tags))
