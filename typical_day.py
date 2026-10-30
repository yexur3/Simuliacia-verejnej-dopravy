from collections import defaultdict
from datetime import datetime

DAY = 86400


def day_seconds(t):
    """Секунди від півночі за місцевим часом."""
    d = datetime.fromtimestamp(t)
    return d.hour * 3600 + d.minute * 60 + d.second


def make_typical_day(trips, trip_type, completeness, min_comp):
    """
    Зводить рейси з різних днів в один "типовий день" 00:00-24:00.
    - Рейси з повнотою нижче min_comp відкидаємо (їх видно лише на кількох зупинках).
    - Якщо одну й ту саму годину доби маємо з двох різних днів, беремо день, у якого
      більше повних рейсів (сума повноти).
    - Час кожного рейсу переводимо в секунди від півночі.
    Повертає (trips, trip_type) з часом у секундах доби.
    """
    info = {}
    score = defaultdict(lambda: defaultdict(float))     # година -> дата -> сума повноти
    for tid, items in trips.items():
        d = datetime.fromtimestamp(items[0][0])
        c = completeness.get(tid, 0.0)
        info[tid] = (d.date(), d.hour, c)
        score[d.hour][d.date()] += c
    best = {hour: max(per_date, key=per_date.get) for hour, per_date in score.items()}

    out_trips, out_type = {}, {}
    for tid, items in trips.items():
        date, hour, c = info[tid]
        if c < min_comp or date != best[hour]:
            continue
        shift = day_seconds(items[0][0]) - items[0][0]
        shifted = [(t + shift, s) for t, s in items]
        out_trips[tid] = shifted
        out_type[tid] = trip_type[tid]
        if shifted[-1][0] > DAY:
            # Рейс переходить через північ: його кінець дублюємо на початок доби
            out_trips[tid + "~"] = [(t - DAY, s) for t, s in shifted]
            out_type[tid + "~"] = trip_type[tid]
    return out_trips, out_type