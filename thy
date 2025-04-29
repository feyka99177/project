from flask import Flask, jsonify, abort
import sqlite3
import csv

app = Flask(__name__)

BOTTOMS_CSV = 'bottoms.csv'
FINDS_DB = 'finds.db'

places_map = {}
findings_map = {}
finds_list = []

def load_data():
    global places_map, findings_map, finds_list

    # Загрузка данных из SQLite
    conn = sqlite3.connect(FINDS_DB)
    cur = conn.cursor()
    
    # Загрузка мест
    cur.execute("SELECT id, place FROM Places")
    places_map = {place: pid for pid, place in cur.fetchall()}
    
    # Загрузка типов находок
    cur.execute("SELECT id, find_type, value FROM Findings")
    findings_map = {
        fid: (ftype, val) for fid, ftype, val in cur.fetchall()
    }
    conn.close()

    # Загрузка данных из CSV
    finds_list.clear()
    with open(BOTTOMS_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            finds_list.append((
                int(row['id']),
                row['find'],
                int(row['type_id']),
                int(row['place_id'])
            ))

# Инициализация данных при старте
load_data()

@app.route('/jewelry/<place>/')
def get_jewelry(place):
    if place not in places_map:
        abort(404, description="Place not found")
    
    place_id = places_map[place]
    filtered = []
    
    for _, find_name, type_id, pid in finds_list:
        if pid == place_id and type_id in findings_map:
            _, val = findings_map[type_id]
            filtered.append((find_name, val))
    
    if not filtered:
        return jsonify([])
    
    # Сортировка по убыванию значения и имени
    filtered.sort(key=lambda x: (-x[1], x[0]))
    
    # Выбор топ-5 с учетом одинаковых значений
    top5 = filtered[:5]
    if len(filtered) > 5:
        last_val = top5[-1][1]
        for item in filtered[5:]:
            if item[1] == last_val:
                top5.append(item)
            else:
                break
    
    result = [item[0] for item in top5]
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
