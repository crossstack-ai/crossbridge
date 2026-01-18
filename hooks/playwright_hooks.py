"""
CrossBridge Playwright Hook Integration

Lightweight Playwright hooks that emit execution events to CrossBridge.

Installation:
    Add to playwright.config.ts or test setup:
    
    import { crossbridgeReporter } from 'crossbridge/hooks/playwright_hooks';
    
    export default defineConfig({
      reporter: [
        ['html'],
        [crossbridgeReporter]
      ]
    });

Or use programmatic API in test files:
    
    import { test } from '@playwright/test';
    import { emitTestEnd } from 'crossbridge/hooks/playwright_hooks';
    
    test.afterEach(async ({}, testInfo) => {
      await emitTestEnd(testInfo);
    });
"""

# Python wrapper for Playwright hooks
# The actual implementation would be in TypeScript/JavaScript

PLAYWRIGHT_HOOK_TEMPLATE = """
// CrossBridge Playwright Hook (TypeScript)
// Save as: playwright-crossbridge-hook.ts

import type { Reporter, TestCase, TestResult } from '@playwright/test/reporter';
import axios from 'axios';

interface CrossBridgeEvent {
  event_type: string;
  framework: string;
  test_id: string;
  timestamp: string;
  status?: string;
  duration_ms?: number;
  error_message?: string;
  stack_trace?: string;
  metadata?: Record<string, any>;
}

class CrossBridgeReporter implements Reporter {
  private apiUrl: string;
  private enabled: boolean;

  constructor() {
    this.apiUrl = process.env.CROSSBRIDGE_API_URL || 'http://localhost:8000/api/events';
    this.enabled = process.env.CROSSBRIDGE_HOOKS_ENABLED !== 'false';
  }

  onTestBegin(test: TestCase, result: TestResult) {
    if (!this.enabled) return;

    const event: CrossBridgeEvent = {
      event_type: 'test_start',
      framework: 'playwright',
      test_id: test.titlePath().join(' > '),
      timestamp: new Date().toISOString(),
      metadata: {
        file: test.location.file,
        line: test.location.line,
        tags: test.tags
      }
    };

    this.emitEvent(event);
  }

  onTestEnd(test: TestCase, result: TestResult) {
    if (!this.enabled) return;

    const event: CrossBridgeEvent = {
      event_type: 'test_end',
      framework: 'playwright',
      test_id: test.titlePath().join(' > '),
      timestamp: new Date().toISOString(),
      status: result.status,
      duration_ms: result.duration,
      error_message: result.error?.message,
      stack_trace: result.error?.stack,
      metadata: {
        file: test.location.file,
        line: test.location.line,
        retry: result.retry,
        attachments: result.attachments.length
      }
    };

    this.emitEvent(event);
  }

  private async emitEvent(event: CrossBridgeEvent) {
    try {
      await axios.post(this.apiUrl, event, {
        timeout: 1000, // 1 second timeout
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      // Never fail test due to hook errors
      console.warn('CrossBridge: Failed to emit event', error.message);
    }
  }
}

export default CrossBridgeReporter;

// Alternative: Inline hook for test files
export async function emitTestEnd(testInfo: any) {
  if (process.env.CROSSBRIDGE_HOOKS_ENABLED === 'false') return;

  const event = {
    event_type: 'test_end',
    framework: 'playwright',
    test_id: testInfo.titlePath.join(' > '),
    timestamp: new Date().toISOString(),
    status: testInfo.status,
    duration_ms: testInfo.duration
  };

  try {
    await fetch(process.env.CROSSBRIDGE_API_URL || 'http://localhost:8000/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event)
    });
  } catch (error) {
    // Silently fail
  }
}

// Usage in test:
// test.afterEach(async ({}, testInfo) => {
//   await emitTestEnd(testInfo);
// });
"""

def get_playwright_hook_code() -> str:
    """Returns the TypeScript code for Playwright hook integration"""
    return PLAYWRIGHT_HOOK_TEMPLATE
