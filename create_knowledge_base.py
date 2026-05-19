import time
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("🔄 Создаём File Search Store...\n")

store = client.file_search_stores.create(
    config={'display_name': 'Zhubanov University Knowledge Base 2026'}
)

print(f"✅ Store создан!")
print(f"STORE NAME (ОБЯЗАТЕЛЬНО СОХРАНИ):")
print(store.name)
print("=" * 80)

# ===================== ФАЙЛЫ =====================
files_to_upload = [
    "knowledge_base/faq_exact.json",
    "knowledge_base/applicant_calendar.docx",
    "knowledge_base/doctor.pdf",
    "knowledge_base/poriyadok.txt",
    "knowledge_base/poslearmii.pdf",
    "knowledge_base/priem.pdf",
    "knowledge_base/specexam.txt",
    "knowledge_base/stoimobuch.pdf",
    "knowledge_base/stoiim.docx",
]


for file_path in files_to_upload:
    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден: {file_path}")
        continue

    print(f"\n📤 Загружаем: {file_path}")

    # Загружаем и получаем имя операции (строку)
    operation_name = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store.name,
        config={'display_name': os.path.basename(file_path)}
    )

    print(f"   Операция запущена: {operation_name}")

    # Проверяем статус
    while True:
        operation = client.operations.get(operation_name)

        if operation.done:
            break

        print("   ⏳ Индексация... ждём 5 сек")
        time.sleep(5)

    # Проверка результата
    if operation.error:
        print(f"❌ Ошибка: {operation.error}")
    else:
        print(f"✅ Успешно загружен и проиндексирован: {file_path}")

print("\n🎉 ГОТОВО! Теперь используй STORE NAME в основном приложении.")