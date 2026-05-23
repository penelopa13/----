import time
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

STORE_NAME = "fileSearchStores/zhubanov-university-knowled-hja9jooexibf"

print(f"📦 Store: {STORE_NAME}")
print("=" * 80)

files_to_upload = [
    "knowledge_base/scores.docx",

]

for file_path in files_to_upload:
    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден: {file_path}")
        continue

    print(f"\n📤 Загружаем: {file_path}")

    try:
        # Запускаем загрузку
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=STORE_NAME,
            config={'display_name': os.path.basename(file_path)}
        )

        print(f"   Операция запущена: {operation.name if hasattr(operation, 'name') else operation}")

        # Ожидаем завершения
        max_attempts = 5
        for attempt in range(max_attempts):
            if getattr(operation, 'done', False):
                break

            print(f"   ⏳ Индексация... ({attempt+1}/{max_attempts})")
            time.sleep(6)

            # Важно: передаём сам объект operation, а не строку!
            operation = client.operations.get(operation)

        # Финальная проверка
        if getattr(operation, 'error', None):
            print(f"❌ Ошибка: {operation.error}")
        else:
            print(f"✅ Успешно загружен: {file_path}")

    except Exception as e:
        print(f"❌ Исключение при загрузке {file_path}: {e}")

print("\n🎉 ГОТОВО!")