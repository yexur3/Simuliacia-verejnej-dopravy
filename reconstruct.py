import math
import statistics
from collections import defaultdict
from datetime import datetime


def to_seconds(iso):
    """'2026-10-27T08:15:00.000Z' -> секунди від початку епохи"""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def merge_order(sequences):
    """
    sequences: списки stopId (кожен у порядку руху), найдовший перший.
    Повертає один спільний порядок зупинок для лінії.
    Нову зупинку додаємо лише тоді, коли її місце однозначне:
    між двома відомими, або на самому початку/кінці лінії.
    """
    order = list(sequences[0])
    in_order = set(order)
    for seq in sequences[1:]:
        known_pos = [i for i, s in enumerate(seq) if s in in_order]
        if not known_pos:
            continue   # нема за що зачепитися
        first, last_i = known_pos[0], known_pos[-1]

        # Невідомі зупинки перед першою відомою: лише якщо вона початок лінії
        lead = seq[:first]
        if lead and order[0] == seq[first]:
            order[0:0] = lead
            in_order.update(lead)

        # Невідомі зупинки між відомими: вставляємо після попередньої відомої
        prev = seq[first]
        for s in seq[first + 1:last_i + 1]:
            if s in in_order:
                prev = s
            else:
                order.insert(order.index(prev) + 1, s)
                in_order.add(s)
                prev = s

        # Невідомі зупинки після останньої відомої: лише якщо вона кінець лінії
        trail = seq[last_i + 1:]
        if trail and order[-1] == seq[last_i]:
            order.extend(trail)
            in_order.update(trail)
    return order


MAX_DETOUR = 4                 # шлях через проміжні зупинки >4x довший за пряму = підозрілий об'їзд
MAX_SPEED = 70 / 3.6           # м/с: швидше за 70 км/год по такому шляху автобус їхати не міг


def fill_trip(known, order, cum, pos):
    """
    known: {stopId: час}. order: спільний порядок. cum: накопичена відстань по order.
    pos: {stopId: (x, y)} у МЕТРАХ (потрібно для перевірки швидкості).
    Повертає [(час, stopId), ...] від першої до останньої відомої зупинки.
    """
    idx = {s: i for i, s in enumerate(order)}
    pts = sorted((idx[s], t) for s, t in known.items() if s in idx)

    # Час має зростати разом з індексом; точки, що ламають це, відкидаємо
    clean = []
    for i, t in pts:
        if not clean or t >= clean[-1][1]:
            clean.append((i, t))

    result = []
    for (i1, t1), (i2, t2) in zip(clean, clean[1:]):
        span = cum[i2] - cum[i1]
        ax, ay = pos[order[i1]]
        bx, by = pos[order[i2]]
        direct = math.hypot(bx - ax, by - ay)
        detour = direct > 0 and span > MAX_DETOUR * direct
        too_fast = (t2 - t1) <= 0 or span / (t2 - t1) > MAX_SPEED
        if detour and too_fast:
            # Об'їзд, який неможливо проїхати за відомий час (збій у порядку зупинок):
            # не вигадуємо проміжні зупинки, з'єднуємо дві відомі напряму.
            # Справжня петля (об'їзд, на який вистачає часу) заповнюється як звичайно.
            result.append((t1, order[i1]))
            continue
        for j in range(i1, i2):
            frac = (cum[j] - cum[i1]) / span if span > 0 else 0
            result.append((t1 + (t2 - t1) * frac, order[j]))
    if clean:
        result.append((clean[-1][1], order[clean[-1][0]]))
    return result


RUN_GAP = 4 * 3600   # пауза між двома відомими часами одного tripId довша за це = різні дні


def collect_runs(departures, valid_stops=None):
    """
    Розбиває записи на окремі проїзди. Один tripId у розкладі повторюється щодня,
    тож записи з різних днів не можна зливати в один рейс.
    Повертає (runs, group, vtype): runs[id] = {stopId: час}.
    """
    by_trip = defaultdict(list)    # tripId -> [(час, stopId)]
    meta = {}
    for d in departures.values():
        if not (d.get("tripId") and d.get("stopId") and d.get("scheduleTime")):
            continue
        if valid_stops is not None and d["stopId"] not in valid_stops:
            continue
        by_trip[d["tripId"]].append((to_seconds(d["scheduleTime"]), d["stopId"]))
        meta[d["tripId"]] = (d.get("routeId"), d.get("direction"), d.get("vehicleType"))

    runs, group, vtype = {}, {}, {}
    for tid, items in by_trip.items():
        items.sort()
        chunks, cur = [], []
        for t, s in items:
            if cur and t - cur[-1][0] > RUN_GAP:
                chunks.append(cur)
                cur = []
            cur.append((t, s))
        chunks.append(cur)
        for n, chunk in enumerate(chunks):
            rid = tid if len(chunks) == 1 else f"{tid}#{n}"
            known = {}
            for t, s in chunk:
                known.setdefault(s, t)         # якщо зупинка двічі, лишаємо раніший час
            runs[rid] = known
            group[rid] = (meta[tid][0], meta[tid][1])
            vtype[rid] = meta[tid][2]
    return runs, group, vtype


def extend_run(filled, order, idx, D):
    """
    Добудовує рейс до кінцевих зупинок лінії за типовим часом проїзду між сусідніми
    зупинками (D[i] = секунди від order[i] до order[i+1]). Йдемо лише по тих сусідніх
    парах, які справді бачили в даних, тож "вигадані" стрибки неможливі.
    """
    first_i, last_i = idx[filled[0][1]], idx[filled[-1][1]]
    out = list(filled)
    t, j = filled[-1][0], last_i
    while j + 1 < len(order) and j in D:
        t += D[j]
        j += 1
        out.append((t, order[j]))
    head = []
    t, j = filled[0][0], first_i
    while j - 1 >= 0 and (j - 1) in D:
        t -= D[j - 1]
        j -= 1
        head.append((t, order[j]))
    return head[::-1] + out


def build_trips(departures, pos):
    """
    departures: словник із departures.json. pos: {stopId: (x, y)} у метрах.
    Повертає (trips, trip_type), де trips = {tripId: [(час, stopId), ...]}.
    """
    # 1. Проїзди: run id -> {stopId: час}; той самий tripId з різних днів не зливаємо
    known_by_trip, trip_group, trip_type = collect_runs(departures, set(pos))

    # 2. Групуємо рейси за лінією і напрямком
    groups = defaultdict(list)
    for tid, group in trip_group.items():
        groups[group].append(tid)

    trips = {}
    for group, tids in groups.items():
        # рейси цієї групи, найдовший (за кількістю відомих зупинок) перший
        tids.sort(key=lambda t: len(known_by_trip[t]), reverse=True)
        seqs = []
        for tid in tids:
            k = known_by_trip[tid]
            seqs.append([s for s, _ in sorted(k.items(), key=lambda kv: kv[1])])
        order = merge_order(seqs)

        # накопичена відстань вздовж order
        cum = [0.0]
        for a, b in zip(order, order[1:]):
            ax, ay = pos[a]
            bx, by = pos[b]
            cum.append(cum[-1] + math.hypot(bx - ax, by - ay))

        # Типові тривалості між сусідніми зупинками порядку (медіана по рейсах лінії)
        idx = {s: i for i, s in enumerate(order)}
        durations = defaultdict(list)
        for tid in tids:
            pts = sorted((idx[s], t) for s, t in known_by_trip[tid].items() if s in idx)
            for (i1, t1), (i2, t2) in zip(pts, pts[1:]):
                if i2 == i1 + 1 and 0 < t2 - t1 < 1800:
                    durations[i1].append(t2 - t1)
        D = {i: statistics.median(v) for i, v in durations.items()}

        for tid in tids:
            filled = fill_trip(known_by_trip[tid], order, cum, pos)
            if len(filled) >= 2:
                trips[tid] = extend_run(filled, order, idx, D)
    return trips, trip_type


def trip_completeness(departures):
    """
    run id -> частка відомих зупинок (0..1) відносно найповнішого рейсу
    тієї ж лінії й напрямку. Низьке значення = рейс проїхав, поки збирач не працював.
    """
    runs, group, _ = collect_runs(departures)
    ref = defaultdict(int)
    for rid, g in group.items():
        ref[g] = max(ref[g], len(runs[rid]))
    return {rid: min(1.0, len(runs[rid]) / ref[group[rid]]) for rid in runs}