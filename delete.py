import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

STORE_NAME = "fileSearchStores/zhubanov-university-knowled-hja9jooexibf"

docs = list(client.file_search_stores.documents.list(parent=STORE_NAME))

for doc in docs:
    if doc.display_name == "faq_exact.json":
        try:
            client.file_search_stores.documents.delete(
                name=doc.name,
                config=types.DeleteDocumentConfig(force=True)
            )
            print(f"🗑 Удалён: {doc.name}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

print("🎉 Готово!")