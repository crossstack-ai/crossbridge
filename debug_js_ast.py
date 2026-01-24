#!/usr/bin/env python3
"""Debug JavaScript AST extraction."""

import re
from core.intelligence.javascript_ast_extractor import JavaScriptASTExtractor
from core.intelligence.models import APICall

code = """
test('e2e test', async ({ page }) => {
    await page.goto('https://example.com');
    await page.click('#button');
    await page.fill('input', 'value');
});
"""

# Test the pattern
pattern = r'(?:test|it|describe)\s*\(\s*[\'"]([^\'"]*)[\'"]'
matches = list(re.finditer(pattern, code))
print(f"Pattern matches: {len(matches)}")
for m in matches:
    print(f"  Match: '{m.group(1)}' at pos {m.start()}-{m.end()}")
    print(f"  After match: {repr(code[m.end():m.end()+50])}")

# Test body extraction
if matches:
    m = matches[0]
    start_pos = m.end()
    brace_count = 0
    in_function = False
    body_start = -1
    test_body = ""
    
    for i in range(start_pos, len(code)):
        if code[i] == '{':
            if not in_function:
                in_function = True
                body_start = i
                print(f"  Found opening brace at {i}")
            brace_count += 1
        elif code[i] == '}':
            brace_count -= 1
            print(f"  Found closing brace at {i}, count={brace_count}")
            if brace_count == 0 and in_function:
                test_body = code[body_start:i+1]
                print(f"  Extracted body: {repr(test_body)}")
                break
    
    # Test UI interaction pattern
    interaction_pattern = r'(?:page|cy)\.(goto|click|fill|type|select|check|visit)\s*\('
    ui_matches = list(re.finditer(interaction_pattern, test_body))
    print(f"\nUI interaction matches: {len(ui_matches)}")
    for m in ui_matches:
        print(f"  Found: {m.group(1)}")

extractor = JavaScriptASTExtractor()
signals = extractor.extract(code, 'e2e test')

print(f"\nExtractor results:")
print(f"  UI interactions: {signals.ui_interactions}")
print(f"  Functions: {signals.functions}")
print(f"  Imports: {signals.imports}")
print(f"  API calls: {signals.api_calls}")
print(f"  Assertions: {signals.assertions}")
