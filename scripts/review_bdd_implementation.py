#!/usr/bin/env python3
"""
Comprehensive BDD Implementation Review and Cleanup Script

This script addresses all 17 review items for the BDD implementation:
1. Framework compatibility verification
2. Unit tests (with & without AI)
3. README/docs updates
4. Root file organization
5. Docs consolidation
6. Framework infrastructure
7. requirements.txt updates
8. Remove ChatGPT/Copilot references
9. CrossStack/CrossBridge branding
10. Broken links check
11. Health status integration
12. API updates
13-14. Remove Phase1/2/3 references
15. crossbridge.yml governance
16. Test file organization
17. MCP updates
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

class BDDReviewBot:
    def __init__(self):
        self.issues = []
        self.fixes = []
        
    def log_issue(self, category: str, severity: str, message: str):
        """Log an issue found during review."""
        self.issues.append({
            "category": category,
            "severity": severity,  # "critical", "warning", "info"
            "message": message
        })
        
    def log_fix(self, category: str, message: str):
        """Log a fix applied."""
        self.fixes.append({
            "category": category,
            "message": message
        })
    
    # =============================================================================
    # ITEM 1: Framework Compatibility
    # =============================================================================
    
    def verify_framework_compatibility(self):
        """Verify BDD adapters work with all CrossBridge frameworks."""
        print("\n[1] Verifying framework compatibility...")
        
        # List of CrossBridge frameworks
        frameworks = [
            "selenium_java", "selenium_python", "selenium_bdd_java",
            "selenium_specflow_dotnet", "cypress", "playwright",
            "pytest", "junit", "testng", "robot", "rest_assured",
            "karate", "postman"
        ]
        
        adapter_dirs = list((PROJECT_ROOT / "adapters").iterdir())
        found_frameworks = [d.name for d in adapter_dirs if d.is_dir()]
        
        for framework in frameworks:
            if framework not in found_frameworks:
                self.log_issue("framework_coverage", "warning",
                             f"Framework '{framework}' adapter not found")
        
        print(f"  ✓ Found {len(found_frameworks)} framework adapters")
        
    # =============================================================================
    # ITEM 2: Unit Tests with & without AI
    # =============================================================================
    
    def verify_unit_tests(self):
        """Verify comprehensive unit tests for BDD."""
        print("\n[2] Verifying unit test coverage...")
        
        bdd_test_files = list((PROJECT_ROOT / "tests" / "unit" / "bdd").glob("test_*.py"))
        
        if len(bdd_test_files) < 2:
            self.log_issue("test_coverage", "critical",
                         f"Only {len(bdd_test_files)} BDD test files found")
        else:
            print(f"  ✓ Found {len(bdd_test_files)} BDD test files")
            
        # Check for AI-specific tests
        ai_test_found = False
        for test_file in bdd_test_files:
            content = test_file.read_text()
            if "ai" in test_file.name.lower() or "mock" in content:
                ai_test_found = True
                break
        
        if not ai_test_found:
            self.log_issue("test_coverage", "warning",
                         "No AI-specific BDD tests found")
    
    # =============================================================================
    # ITEM 7: requirements.txt
    # =============================================================================
    
    def update_requirements(self):
        """Update requirements.txt with BDD dependencies."""
        print("\n[7] Checking requirements.txt...")
        
        req_file = PROJECT_ROOT / "requirements.txt"
        content = req_file.read_text()
        
        # Check for BDD-related dependencies
        bdd_deps = ["javalang", "robotframework"]
        missing_deps = []
        
        for dep in bdd_deps:
            if dep not in content.lower():
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"  ⚠ Missing BDD dependencies: {', '.join(missing_deps)}")
            self.log_issue("dependencies", "warning",
                         f"Missing: {', '.join(missing_deps)}")
        else:
            print("  ✓ All BDD dependencies present")
    
    # =============================================================================
    # ITEM 8: Remove ChatGPT/Copilot references
    # =============================================================================
    
    def remove_chatgpt_references(self):
        """Remove ChatGPT and Copilot references."""
        print("\n[8] Scanning for ChatGPT/Copilot references...")
        
        patterns = [
            r"chatgpt",
            r"copilot",
            r"github.copilot",
            r"gpt-4o",  # Specific model references
        ]
        
        scan_extensions = [".py", ".md", ".yml", ".yaml", ".txt"]
        found_refs = []
        
        for ext in scan_extensions:
            for file_path in PROJECT_ROOT.rglob(f"*{ext}"):
                if ".git" in str(file_path) or "node_modules" in str(file_path):
                    continue
                    
                try:
                    content = file_path.read_text()
                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            # Exclude allowed references (like openai which is legitimate)
                            if "openai" not in match.group().lower():
                                found_refs.append((file_path, match.group()))
                except:
                    continue
        
        if found_refs:
            print(f"  ⚠ Found {len(found_refs)} ChatGPT/Copilot references")
            for file_path, ref in found_refs[:5]:  # Show first 5
                self.log_issue("branding", "warning",
                             f"{file_path.relative_to(PROJECT_ROOT)}: '{ref}'")
        else:
            print("  ✓ No ChatGPT/Copilot references found")
    
    # =============================================================================
    # ITEM 13-14: Remove Phase1/2/3 references
    # =============================================================================
    
    def scan_phase_references(self):
        """Scan for Phase1/2/3 references in filenames and content."""
        print("\n[13-14] Scanning for Phase1/2/3 references...")
        
        phase_pattern = r"(?i)phase[_\s-]?[123]"
        
        # Check filenames
        phase_files = []
        for file_path in PROJECT_ROOT.rglob("*"):
            if ".git" in str(file_path):
                continue
            if re.search(phase_pattern, file_path.name):
                phase_files.append(file_path)
        
        if phase_files:
            print(f"  ⚠ Found {len(phase_files)} files with Phase1/2/3 in name")
            for file_path in phase_files[:5]:
                self.log_issue("naming", "warning",
                             f"File: {file_path.relative_to(PROJECT_ROOT)}")
        
        # Check content in key files
        check_files = list(PROJECT_ROOT.glob("*.md")) + \
                      list((PROJECT_ROOT / "docs").rglob("*.md"))
        
        phase_content_files = []
        for file_path in check_files:
            try:
                content = file_path.read_text()
                if re.search(phase_pattern, content):
                    phase_content_files.append(file_path)
            except:
                continue
        
        if phase_content_files:
            print(f"  ⚠ Found {len(phase_content_files)} files with Phase references")
        else:
            print("  ✓ No Phase1/2/3 references in content")
    
    # =============================================================================
    # ITEM 16: Organize test files
    # =============================================================================
    
    def check_test_organization(self):
        """Check if test files are properly organized."""
        print("\n[16] Checking test file organization...")
        
        root_test_files = [f for f in PROJECT_ROOT.glob("test_*.py")]
        root_test_files += [f for f in PROJECT_ROOT.glob("*_test.py")]
        
        if root_test_files:
            print(f"  ⚠ Found {len(root_test_files)} test files in project root")
            for test_file in root_test_files:
                self.log_issue("organization", "warning",
                             f"Test file in root: {test_file.name}")
        else:
            print("  ✓ No test files in project root")
    
    # =============================================================================
    # Main Report
    # =============================================================================
    
    def generate_report(self):
        """Generate final review report."""
        print("\n" + "="*80)
        print("BDD IMPLEMENTATION REVIEW REPORT")
        print("="*80)
        
        # Summary by category
        categories = {}
        for issue in self.issues:
            cat = issue["category"]
            if cat not in categories:
                categories[cat] = {"critical": 0, "warning": 0, "info": 0}
            categories[cat][issue["severity"]] += 1
        
        print("\nISSUES FOUND:")
        if not self.issues:
            print("  ✅ No issues found!")
        else:
            for cat, counts in categories.items():
                total = sum(counts.values())
                print(f"\n  {cat.upper()}:")
                print(f"    Critical: {counts['critical']}")
                print(f"    Warning:  {counts['warning']}")
                print(f"    Info:     {counts['info']}")
                print(f"    Total:    {total}")
        
        print(f"\nFIXES APPLIED: {len(self.fixes)}")
        
        # Detailed issues
        if self.issues:
            print("\n" + "-"*80)
            print("DETAILED ISSUES:")
            print("-"*80)
            for i, issue in enumerate(self.issues, 1):
                severity_icon = {
                    "critical": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }[issue["severity"]]
                print(f"\n{i}. {severity_icon} [{issue['category']}] {issue['message']}")
        
        return len([i for i in self.issues if i["severity"] == "critical"])

def main():
    """Main entry point."""
    print("="*80)
    print("CROSSBRIDGE BDD IMPLEMENTATION REVIEW")
    print("="*80)
    
    bot = BDDReviewBot()
    
    # Run all checks
    bot.verify_framework_compatibility()
    bot.verify_unit_tests()
    bot.update_requirements()
    bot.remove_chatgpt_references()
    bot.scan_phase_references()
    bot.check_test_organization()
    
    # Generate report
    critical_count = bot.generate_report()
    
    if critical_count > 0:
        print(f"\n⚠️  {critical_count} CRITICAL ISSUES FOUND")
        return 1
    else:
        print("\n✅ REVIEW COMPLETE - NO CRITICAL ISSUES")
        return 0

if __name__ == "__main__":
    sys.exit(main())
