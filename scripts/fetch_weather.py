# scripts/fetch_weather.py
"""Fetch real daily weather history for the project's cities and write the training and test sets.

One call to Open-Meteo's archive brings every city's daily readings since START. The last 365
complete days become the test set, everything before them the training set, so the model is judged
on days that came after anything it learned from. Both files use the FEATURES columns plus target,
the shape scripts/train_model.py and scripts/evaluate_model.py already read.

Usage, from the project root:
  python -m scripts.fetch_weather
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date, timedelta

import pandas as pd

from src.config import CITIES, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.data_preprocessing.preprocess import DAILY_FIELDS, FEATURES, make_features

START = '2015-01-01'


def fetch_history(end):
    names = list(CITIES)
    q = {
        'latitude': ','.join(str(CITIES[n][0]) for n in names),
        'longitude': ','.join(str(CITIES[n][1]) for n in names),
        'start_date': START, 'end_date': end,
        'daily': ','.join(DAILY_FIELDS), 'timezone': 'Asia/Kolkata',
    }
    url = 'https://archive-api.open-meteo.com/v1/archive?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=180) as r:
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
    end = date.today() - timedelta(days=1)        # yesterday: complete days only
    split = end - timedelta(days=365)             # the last year is the test set
    raw = fetch_history(end.isoformat())
    raw.to_csv(os.path.join(RAW_DATA_DIR, 'daily_history.csv'), index=False)

    df = make_features(raw).dropna(subset=['target'])
    day = pd.to_datetime(df['date']).dt.date
    train, test = df[day < split], df[day >= split]
    train[FEATURES + ['target']].to_csv(os.path.join(PROCESSED_DATA_DIR, 'processed_training_data.csv'), index=False)
    test[FEATURES + ['target']].to_csv(os.path.join(PROCESSED_DATA_DIR, 'processed_test_data.csv'), index=False)
    meta = {'start': START, 'split': split.isoformat(), 'end': end.isoformat(),
            'train_rows': len(train), 'test_rows': len(test), 'cities': list(CITIES)}
    with open(os.path.join(PROCESSED_DATA_DIR, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=1)

    print(f"{len(raw)} city-days fetched for {len(CITIES)} cities, {START} to {end}")
    print(f"train: {len(train)} rows (before {split})   test: {len(test)} rows ({split} to {end})")
    print(f"target: next day's max temperature. features: {len(FEATURES)}")


if __name__ == '__main__':
    main()
