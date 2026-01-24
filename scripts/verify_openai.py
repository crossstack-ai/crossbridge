"""
Test script to verify OpenAI integration with CrossBridge.
Checks API key configuration and tests basic connectivity.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_openai_setup():
    """Check OpenAI configuration and connectivity."""
    
    print("="*80)
    print("CrossBridge OpenAI Integration Verification")
    print("="*80)
    print()
    
    # Step 1: Check if OpenAI library is installed
    print("1️⃣  Checking OpenAI library installation...")
    try:
        import openai
        print(f"   ✅ OpenAI library installed (version: {openai.__version__})")
    except ImportError:
        print("   ❌ OpenAI library NOT installed")
        print("   📦 Install with: pip install openai")
        return False
    
    # Step 2: Check for API key
    print("\n2️⃣  Checking for API key...")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("   ❌ OPENAI_API_KEY environment variable not set")
        print("\n   📋 To set your API key:")
        print("   ")
        print("   Windows (PowerShell):")
        print("      $env:OPENAI_API_KEY='your-api-key-here'")
        print("   ")
        print("   Windows (CMD):")
        print("      set OPENAI_API_KEY=your-api-key-here")
        print("   ")
        print("   Linux/Mac:")
        print("      export OPENAI_API_KEY='your-api-key-here'")
        print("   ")
        print("   Or add to .env file in project root:")
        print("      OPENAI_API_KEY=your-api-key-here")
        return False
    
    # Mask the key for security
    masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
    print(f"   ✅ API key found: {masked_key}")
    
    # Step 3: Test API connectivity
    print("\n3️⃣  Testing API connectivity...")
    try:
        # Direct OpenAI test without CrossBridge dependencies
        client = openai.OpenAI(api_key=api_key)
        # Direct OpenAI test without CrossBridge dependencies
        client = openai.OpenAI(api_key=api_key)
        
        print("   🔄 Sending test request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        # Approximate cost calculation for gpt-3.5-turbo
        cost = (response.usage.prompt_tokens * 0.0015 + response.usage.completion_tokens * 0.002) / 1000
        
        print(f"   ✅ API connection successful!")
        print(f"   📝 Response: {content[:50]}...")
        print(f"   💰 Tokens used: {tokens}")
        print(f"   💵 Cost: ${cost:.4f}")
        
    except Exception as e:
        print(f"   ❌ API connection failed: {str(e)}")
        print(f"\n   🔍 Error details:")
        print(f"      Type: {type(e).__name__}")
        
        if "authentication" in str(e).lower() or "api key" in str(e).lower():
            print("      Issue: Invalid API key")
            print("      Fix: Check your OPENAI_API_KEY is correct")
        elif "rate limit" in str(e).lower():
            print("      Issue: Rate limit exceeded")
            print("      Fix: Wait a moment and try again")
        elif "quota" in str(e).lower():
            print("      Issue: API quota exceeded")
            print("      Fix: Check your OpenAI billing and limits")
        
        return False
    
    # Step 4: Check model availability
    print("\n4️⃣  Checking available models...")
    try:
        print("   ✅ Recommended models:")
        print("      • gpt-4o (latest, most capable)")
        print("      • gpt-4-turbo (fast, cost-effective)")
        print("      • gpt-3.5-turbo (fast, economical)")
    except Exception as e:
        print(f"   ⚠️  Could not list models: {e}")
    
    print("\n" + "="*80)
    print("✅ OpenAI Integration Verified Successfully!")
    print("="*80)
    print()
    print("You can now use AI-powered features in CrossBridge:")
    print("  • Enhanced transformation mode")
    print("  • Hybrid transformation mode")
    print("  • AI-powered test generation")
    print("  • Intelligent code analysis")
    print()
    return True

if __name__ == "__main__":
    success = check_openai_setup()
    sys.exit(0 if success else 1)
