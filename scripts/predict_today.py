# scripts/predict_today.py
"""Score today's readings with the trained model and publish tomorrow's estimate for every city.

Reads the last three days plus today from Open-Meteo's forecast API (the same daily fields the
model was trained on), builds today's feature row per city, predicts tomorrow's maximum
temperature, and writes a JSON file the site displays. It also reports the model's error on the
held-out test year next to the plain "carry today forward" baseline, so the number can be judged.

Usage, from the project root:
  python -m scripts.predict_today
  python -m scripts.predict_today --out ../climate-site/assets/forecast.json
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import pandas as pd
from sklearn.metrics import mean_absolute_error

from src.config import CITIES, MODEL_DIR, PROCESSED_DATA_DIR, RESULTS_DIR
from src.data_preprocessing.preprocess import DAILY_FIELDS, FEATURES, make_features
from src.models.model import load_model

IST = timezone(timedelta(hours=5, minutes=30))


def fetch_recent():
    names = list(CITIES)
    q = {
        'latitude': ','.join(str(CITIES[n][0]) for n in names),
        'longitude': ','.join(str(CITIES[n][1]) for n in names),
        'daily': ','.join(DAILY_FIELDS), 'past_days': 3, 'forecast_days': 2, 'timezone': 'Asia/Kolkata',
    }
    url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    frames = []
    for name, d in zip(names, data if isinstance(data, list) else [data]):
        f = pd.DataFrame({'date': d['daily']['time'], **{col: d['daily'][k] for k, col in DAILY_FIELDS.items()}})
        f.insert(0, 'city', name)
        f.insert(1, 'lat', CITIES[name][0])
        f.insert(2, 'lon', CITIES[name][1])
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(RESULTS_DIR, 'forecast.json'))
    a = ap.parse_args()

    model = load_model(os.path.join(MODEL_DIR, 'trained_model.pkl'))
    with open(os.path.join(PROCESSED_DATA_DIR, 'meta.json'), encoding='utf-8') as f:
        meta = json.load(f)

    # How good is it, on the year it never saw, against the simplest possible forecast?
    test = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'processed_test_data.csv'))
    mae = mean_absolute_error(test['target'], model.predict(test[FEATURES]))
    persistence = mean_absolute_error(test['target'], test['tmax'])

    recent = make_features(fetch_recent())
    today = datetime.now(IST).date()
    rows = recent[recent['date'] == today.isoformat()].reset_index(drop=True)
    feed = recent[recent['date'] == (today + timedelta(days=1)).isoformat()].set_index('city')['tmax']
    preds = model.predict(rows[FEATURES].astype(float))
    cities = [{'city': r['city'], 'today_max': float(r['tmax']), 'model_tomorrow_max': round(float(p), 1),
               'feed_tomorrow_max': float(feed[r['city']])} for r, p in zip(rows.to_dict('records'), preds)]

    result = {
        'generated_at': datetime.now(IST).isoformat(timespec='minutes'), 'for_date': (today + timedelta(days=1)).isoformat(),
        'model': type(model).__name__, 'trained_from': meta['start'], 'trained_through': meta['split'],
        'tested_through': meta['end'], 'test_days': meta['test_rows'],
        'test_mae': round(float(mae), 2), 'persistence_mae': round(float(persistence), 2), 'cities': cities,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1)

    print(f"model {result['model']}: mean error {result['test_mae']} C on {meta['test_rows']} held-out city-days "
          f"({meta['split']} to {meta['end']}); carrying today forward: {result['persistence_mae']} C")
    print(f"\nTomorrow ({result['for_date']}), max temperature:\n{'city':<12}{'today':>8}{'ours':>8}{'feed':>8}")
    for c in cities:
        print(f"{c['city']:<12}{c['today_max']:>8.1f}{c['model_tomorrow_max']:>8.1f}{c['feed_tomorrow_max']:>8.1f}")
    print(f"\nWritten to {a.out}")


if __name__ == '__main__':
    main()
