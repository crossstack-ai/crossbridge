"""
Comprehensive verification of unified configuration support across all frameworks.
"""

import logging
from core.execution.intelligence.rules.engine import load_rule_pack

# Suppress debug logs
logging.basicConfig(level=logging.ERROR)

# All 13 supported frameworks
FRAMEWORKS = [
    'selenium', 'pytest', 'robot', 'playwright', 'cypress',
    'restassured', 'cucumber', 'behave', 'junit', 'testng',
    'specflow', 'nunit', 'generic'
]

print("=" * 80)
print("Crossbridge Unified Configuration - Framework Support Verification")
print("=" * 80)
print(f"\nTotal Frameworks Supported: {len(FRAMEWORKS)}")
print()

results = []
for framework in FRAMEWORKS:
    try:
        rule_pack = load_rule_pack(framework)
        rule_count = len(rule_pack.rules)
        status = "[OK]" if rule_count > 0 else "[WARN]"
        results.append((framework, rule_count, True))
        print(f"{status} {framework:15} - {rule_count:3} rules loaded")
    except Exception as e:
        results.append((framework, 0, False))
        print(f"[FAIL] {framework:15} - Error: {e}")

print()
print("=" * 80)
success_count = len([r for r in results if r[2] and r[1] > 0])
print(f"Summary: {success_count}/{len(FRAMEWORKS)} frameworks loaded successfully")
print("=" * 80)

if success_count == len(FRAMEWORKS):
    print("\n✅ ALL FRAMEWORKS SUPPORTED!")
else:
    print(f"\n⚠️  {len(FRAMEWORKS) - success_count} frameworks failed to load")
