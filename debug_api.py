"""Quick script to diagnose Gemini API errors."""
from google import genai

API_KEY = "AIzaSyAHzLULEg_jjzLSdXpBYo9fn7acuSU7T6Y"

client = genai.Client(api_key=API_KEY)
print("Client created OK")

try:
    r = client.models.generate_content(model="gemini-2.0-flash", contents="Say hi")
    print("SUCCESS:", r.text)
except Exception as e:
    print(f"ERROR TYPE: {type(e).__name__}")
    print(f"ERROR MSG: {e}")
