import ctypes
import json
import os
import shutil
import time
import traceback
from datetime import datetime

import requests

URL = "https://opendata.banskabystrica.sk/api/datasets/v1/public-transport/stops/list"
OUT_FILE = "data/departures.json"
LOG_FILE = "data/snapshots.log"
BACKUP_DIR = "data/backup"
INTERVAL_MIN = 10  # як часто опитуємо API


def prevent_sleep():
    """Windows: не дає комп'ютеру заснути, поки скрипт працює (екран може гаснути)."""
    try:
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        print("Сон комп'ютера заблоковано, поки скрипт працює.")
    except Exception:
        print("Не вдалося заблокувати сон автоматично. Вимкни сон у налаштуваннях Windows.")


def load_collected():
    """Читає накопичене. Старі ключі (без часу) перетворює на нові, дублікати зникають."""
    if not os.path.exists(OUT_FILE):
        return {}
    try:
        with open(OUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise SystemExit(f"Не вдалося прочитати {OUT_FILE}: {e}\n"
                         f"Файл НЕ змінено. Перевір його або візьми копію з {BACKUP_DIR}.")
    return {f'{v["tripId"]}|{v["stopId"]}|{v["scheduleTime"]}': v for v in data.values()}


def save_atomic(data):
    """Спершу пишемо в тимчасовий файл, потім підміняємо: обрив живлення не зіпсує дані."""
    tmp = OUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, OUT_FILE)


def daily_backup():
    """Раз на добу копія файлу в data/backup (до першого запису цього дня)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = os.path.join(BACKUP_DIR, f"departures_{datetime.now():%Y-%m-%d}.json")
    if not os.path.exists(name) and os.path.exists(OUT_FILE):
        shutil.copy2(OUT_FILE, name)


def poll(collected):
    """Один запит до API. Повертає кількість нових записів."""
    r = requests.post(URL, json={}, timeout=30)
    r.raise_for_status()
    stops = r.json()
    if not isinstance(stops, list):
        raise ValueError("Незвична відповідь API: " + str(stops)[:200])
    new_count = 0
    for stop in stops:
        if not stop:
            continue
        for dep in (stop.get("departures") or []):
            if not dep:
                continue
            # Час за розкладом у ключі: той самий рейс наступного дня не перезапише сьогоднішній
            key = f'{dep.get("tripId")}|{stop.get("stopId")}|{dep.get("scheduleTime")}'
            if key not in collected:
                new_count += 1
            collected[key] = {
                "tripId": dep.get("tripId"),
                "stopId": stop.get("stopId"),
                "routeId": dep.get("routeId"),
                "routeShortName": dep.get("routeShortName"),
                "vehicleType": dep.get("vehicleType"),
                "direction": dep.get("direction"),
                "scheduleTime": dep.get("scheduleTime"),
                "realTime": dep.get("realTime"),
            }
    return new_count


def main():
    os.makedirs("data", exist_ok=True)
    prevent_sleep()
    collected = load_collected()
    print(f"Завантажено {len(collected)} записів. Опитування кожні {INTERVAL_MIN} хв. Зупинити: Ctrl+C.")
    while True:
        try:
            new_count = poll(collected)
            daily_backup()
            save_atomic(collected)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(datetime.now().isoformat(timespec="seconds") + "\n")
            print(f"[{datetime.now():%d.%m %H:%M:%S}] нових: {new_count}, всього записів: {len(collected)}")
        except Exception:
            traceback.print_exc()   # одна невдала спроба не зупиняє збір на всю ніч
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nЗупинено. Зібрані дані збережено.")