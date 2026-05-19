from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

store = "fileSearchStores/zhubanov-university-knowled-9wr7fjctsylk"

try:
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Какие специальности есть в университете Жубанова?",
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                file_search=types.FileSearch(
                    fileSearchStoreNames=[store]
                )
            )],
            temperature=0.1,
        )
    )
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            print(part.text[:500])
except Exception as e:
    print(f"Ошибка: {e}")