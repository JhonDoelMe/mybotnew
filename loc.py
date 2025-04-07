import csv
import json

# Читаем CSV и создаем словарь
locations = {}
with open('locations.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        oblast_uid = row['location_oblast_uid']
        location_uid = row['location_uid']
        location_title = row['location_title']
        if oblast_uid not in locations:
            locations[oblast_uid] = {}
        locations[oblast_uid][location_uid] = location_title

# Сохраняем в JSON
with open('locations.json', 'w', encoding='utf-8') as jsonfile:
    json.dump(locations, jsonfile, ensure_ascii=False, indent=2)

print("JSON файл создан: locations.json")