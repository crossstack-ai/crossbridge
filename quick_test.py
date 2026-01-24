"""Quick OpenAI connectivity test"""
import os
import openai

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ No API key found")
    exit(1)

print(f"✅ API key: {api_key[:10]}...{api_key[-4:]}")
print("🔄 Testing OpenAI API...")

try:
    client = openai.OpenAI(api_key=api_key, timeout=10.0)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    print(f"✅ SUCCESS! Response: {response.choices[0].message.content}")
    print(f"💰 Tokens: {response.usage.total_tokens}")
except Exception as e:
    print(f"❌ Error: {e}")
