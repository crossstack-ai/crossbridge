# OpenAI Integration Setup Guide

## Prerequisites

✅ **OpenAI library installed** (via `pip install openai anthropic`)

## Step 1: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to **API Keys** section
4. Click **"Create new secret key"**
5. Copy the key (you won't be able to see it again!)

## Step 2: Set the API Key

### Option 1: Environment Variable (Recommended for testing)

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY='sk-your-actual-key-here'
```

**Windows CMD:**
```cmd
set OPENAI_API_KEY=sk-your-actual-key-here
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY='sk-your-actual-key-here'
```

### Option 2: .env File (Recommended for development)

Create a `.env` file in the project root (`d:\Future-work2\crossbridge\.env`):

```env
OPENAI_API_KEY=sk-your-actual-key-here
```

**Important:** Make sure `.env` is in `.gitignore` to avoid committing your API key!

### Option 3: System Environment Variable (Permanent)

**Windows:**
1. Open System Properties → Advanced → Environment Variables
2. Add new User or System variable:
   - Name: `OPENAI_API_KEY`
   - Value: `sk-your-actual-key-here`
3. Restart your terminal/IDE

## Step 3: Verify Integration

Run the verification script:

```bash
python scripts/verify_openai.py
```

Expected output:
```
✅ OpenAI library installed
✅ API key found: sk-proj...
✅ API connection successful!
✅ OpenAI Integration Verified Successfully!
```

## Step 4: Use AI Features in CrossBridge

Once verified, you can use AI-powered features:

### In CLI Interactive Mode:

1. Run: `python run_cli.py`
2. Select Migration or Transformation
3. When prompted for AI settings:
   - Choose **"Public Cloud (OpenAI/Anthropic)"**
   - Select **"OpenAI"**
   - Choose model: `gpt-4o` (recommended) or `gpt-3.5-turbo` (economical)

### Transformation Modes with AI:

- **Enhanced Mode**: Pattern-based transformation with AI assistance
- **Hybrid Mode**: AI-powered transformation with human review markers

### Cost Considerations:

- **gpt-3.5-turbo**: ~$0.002/1K tokens (economical, good for basic transformations)
- **gpt-4-turbo**: ~$0.01/1K tokens (balanced quality and cost)
- **gpt-4o**: ~$0.005/1K tokens (latest, most capable, recommended)

Typical transformation costs: $0.05 - $0.50 per file depending on size and complexity.

## Troubleshooting

### Issue: "Invalid API Key"
- ✅ Check the key starts with `sk-`
- ✅ Verify no extra spaces or quotes
- ✅ Regenerate key in OpenAI dashboard if needed

### Issue: "Rate Limit Exceeded"
- ✅ Wait a few seconds and retry
- ✅ Check your OpenAI usage limits
- ✅ Upgrade to paid tier if needed

### Issue: "Quota Exceeded"
- ✅ Check your OpenAI billing status
- ✅ Add payment method in OpenAI dashboard
- ✅ Check usage limits and quotas

### Issue: "Module not found: openai"
- ✅ Run: `pip install openai anthropic`
- ✅ Check you're using correct Python environment

## Alternative: Anthropic Claude

CrossBridge also supports Anthropic Claude models:

1. Get API key from [Anthropic Console](https://console.anthropic.com/)
2. Set environment variable:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
3. Select "Anthropic" in CLI when prompted

## Support

For issues, check:
- [OpenAI API Status](https://status.openai.com/)
- CrossBridge logs: `~/.crossbridge/logs/`
- GitHub Issues: [CrossBridge Issues](https://github.com/yourusername/crossbridge/issues)
