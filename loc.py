import csv
import json

# Читаем CSV и создаем словарь
locations = {}
oblast_uids = set([
    "3", "4", "5", "8", "9", "10", "11", "12", "13", "14", "15", "16", 
    "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", 
    "28", "29", "30", "31"
])  # Список UID областей из OBLASTS в air_raid.py

with open('locations.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    print("Заголовки колонок:", reader.fieldnames)  # Выводим имена колонок
    
    # Учитываем BOM в имени колонки
    uid_column = '\ufeffUID' if '\ufeffUID' in reader.fieldnames else 'UID'
    
    for row in reader:
        uid = row[uid_column]  # Используем правильное имя колонки
        name = row['Назва']
        
        # Если UID — это область, создаем пустой словарь для нее
        if uid in oblast_uids:
            if uid not in locations:
                locations[uid] = {}
            locations[uid][uid] = name  # Добавляем саму область как локацию
        else:
            # Предполагаем, что это район, и пока пропускаем
            print(f"Район без области: UID={uid}, Назва={name}")

# Сохраняем в JSON
with open('locations.json', 'w', encoding='utf-8') as jsonfile:
    json.dump(locations, jsonfile, ensure_ascii=False, indent=2)

print("JSON файл создан: locations.json")