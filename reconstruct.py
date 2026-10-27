import math
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


def fill_trip(known, order, cum):
    """
    known: {stopId: час}. order: спільний порядок. cum: накопичена відстань по order.
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
        for j in range(i1, i2):
            frac = (cum[j] - cum[i1]) / span if span > 0 else 0
            result.append((t1 + (t2 - t1) * frac, order[j]))
    if clean:
        result.append((clean[-1][1], order[clean[-1][0]]))
    return result


def build_trips(departures, pos):
    """
    departures: словник із departures.json. pos: {stopId: (x, y)}.
    Повертає (trips, trip_type), де trips = {tripId: [(час, stopId), ...]}.
    """
    # 1. tripId -> {stopId: час}, і до якої лінії/напрямку належить рейс
    known_by_trip = defaultdict(dict)
    trip_group = {}
    trip_type = {}
    for d in departures.values():
        if d["stopId"] in pos and d["scheduleTime"] and d["tripId"]:
            known_by_trip[d["tripId"]][d["stopId"]] = to_seconds(d["scheduleTime"])
            trip_group[d["tripId"]] = (d["routeId"], d["direction"])
            trip_type[d["tripId"]] = d["vehicleType"]

    # 2. Групуємо рейси за лінією і напрямком
    groups = defaultdict(list)
    for tid, group in trip_group.items():
        groups[group].append(tid)

    trips = {}
    for group, tids in groups.items():
        # найдовший (за кількістю відомих зупинок) рейс першим
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

        for tid in tids:
            filled = fill_trip(known_by_trip[tid], order, cum)
            if len(filled) >= 2:
                trips[tid] = filled
    return trips, trip_type