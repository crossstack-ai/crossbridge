# AI Model Selection Enhancement

## Summary

Added interactive model selection to CLI AI configuration, allowing users to choose their preferred AI model with economical defaults.

## Changes Made

### 1. Updated AIConfig Default Model
**File:** `core/orchestration/models.py` (Line 89)
- **Before:** `model: str = "gpt-4"` (expensive default)
- **After:** `model: str = "gpt-3.5-turbo"` (economical default)
- **Impact:** 15x cost reduction (~$0.002 vs ~$0.03 per 1K tokens)

### 2. Added CLI Model Selection Prompt
**File:** `cli/prompts.py` (Lines 1063-1100)

**For OpenAI:**
- [1] gpt-3.5-turbo (Default) - Most economical, efficient
- [2] gpt-4 - More capable, higher cost (15x)
- [3] gpt-4-turbo - Latest, faster

**For Anthropic:**
- [1] claude-3-sonnet-20240229 (Default) - Balanced
- [2] claude-3-opus-20240229 - Most capable

**For On-Prem:**
- Custom model name input (defaults to gpt-3.5-turbo)

### 3. Updated Documentation
**File:** `docs/AI_TRANSFORMATION_USAGE.md`
- Added model selection guide
- Cost comparison table
- CLI usage example with model prompts
- Recommendation: Start with gpt-3.5-turbo for most migrations

## Testing

Created `test_model_selection.py` to verify:
- ✅ AIConfig defaults to gpt-3.5-turbo
- ✅ Custom models can be specified
- ✅ Both OpenAI and Anthropic models work

**Test Results:**
```
✓ Default model: gpt-3.5-turbo
✓ Custom model: gpt-4
✓ Anthropic model: claude-3-sonnet-20240229
✅ All AIConfig model tests passed!
```

## User Experience Flow

### Before:
```
Use AI? → Yes
Provider? → OpenAI
API Key? → ****
[Uses hardcoded gpt-4 - expensive!]
```

### After:
```
Use AI? → Yes
Provider? → OpenAI
API Key? → ****
Select Model?
  [1] gpt-3.5-turbo (Default - Economical)
  [2] gpt-4 (More capable, 15x cost)
  [3] gpt-4-turbo (Latest)
Choice: 1
[Uses gpt-3.5-turbo - economical!]
```

## Cost Impact

**Example Migration (100 files, avg 1500 tokens each):**
- **Before (gpt-4):** 150K tokens × $0.03/1K = **$4.50**
- **After (gpt-3.5-turbo):** 150K tokens × $0.002/1K = **$0.30**
- **Savings:** $4.20 (93% cost reduction)

## Available Models

### OpenAI
| Model | Cost/1K Tokens | Speed | Quality | Use Case |
|-------|----------------|-------|---------|----------|
| gpt-3.5-turbo | $0.002 | Fast | Good | Default migrations |
| gpt-4 | $0.030 | Slow | Excellent | Complex transformations |
| gpt-4-turbo | $0.010 | Fast | Excellent | Production workloads |

### Anthropic
| Model | Cost/1K Tokens | Speed | Quality | Use Case |
|-------|----------------|-------|---------|----------|
| claude-3-sonnet | $0.003 | Fast | Very Good | Default migrations |
| claude-3-opus | $0.015 | Moderate | Excellent | Complex transformations |

## Recommendations

1. **Start with gpt-3.5-turbo** (OpenAI) or **claude-3-sonnet** (Anthropic) for most migrations
2. Use **gpt-4** or **claude-3-opus** only for:
   - Complex business logic transformations
   - Unusual Cucumber patterns
   - Custom framework integrations
   - High-stakes production migrations
3. **Monitor costs** using the AI transformation logs (shows tokens + cost per file)
4. **Batch test** with economical models first, then upgrade if needed

## Files Modified

1. ✅ `core/orchestration/models.py` - Changed default model to gpt-3.5-turbo
2. ✅ `cli/prompts.py` - Added model selection prompts for all AI modes
3. ✅ `docs/AI_TRANSFORMATION_USAGE.md` - Updated with model selection guide
4. ✅ `test_model_selection.py` - Created test to verify changes

## Backward Compatibility

- ✅ Existing code without model specification now uses economical gpt-3.5-turbo
- ✅ API callers can still override model in AIConfig
- ✅ CLI provides default but allows customization
- ✅ Fallback to gpt-3.5-turbo in transformation methods unchanged

## Next Steps

Users can now:
1. Run `python run_cli.py`
2. Enable AI
3. Choose their preferred model or accept economical default
4. Save costs while maintaining quality

The most economical and efficient model (gpt-3.5-turbo) is now the default, with easy upgrade options for complex cases.
