# scripts/predict_mumbai.py
"""Predict every day of the Mumbai observation dataset with the trained model.

Aggregates the sub-hourly readings (cleaned_data.csv) into one row per day, maps them onto
the model's daily features (the dataset has no rain or wind speed, so those are NaN, which
HistGradientBoosting handles natively), predicts the next day's maximum temperature for every
day, and writes a JSON of date, actual and predicted that the site charts.

Usage, from the project root:
  python -m scripts.predict_mumbai "C:/Users/ADMIN/Downloads/cleaned_data.csv" --out site/assets/mumbai.json
"""
import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

from src.config import CITIES, MODEL_DIR
from src.data_preprocessing.preprocess import FEATURES, make_features
from src.models.model import load_model

LAT, LON = CITIES['Mumbai']


def daily_rows(csv_path):
    """One row per calendar day from the sub-hourly observations, on a continuous date index."""
    df = pd.read_csv(csv_path, usecols=['Time', 'Temperature', 'Relative Humidity', 'Pressure', 'Wind Direction'])
    t = pd.to_datetime(df['Time'], errors='coerce')
    df = df[t.notna()].copy()
    df['date'] = t[t.notna()].dt.normalize()
    g = df.groupby('date')
    rad = np.radians(df['Wind Direction'])
    day = pd.DataFrame({
        'tmax': g['Temperature'].max(), 'tmin': g['Temperature'].min(), 'tmean': g['Temperature'].mean(),
        'rh': g['Relative Humidity'].mean(), 'pres': g['Pressure'].mean(),
        'wdir': np.degrees(np.arctan2(np.sin(rad).groupby(df['date']).mean(),
                                      np.cos(rad).groupby(df['date']).mean())) % 360,
        'n': g.size(),
    })
    day = day[day['n'] >= 10]                       # a day needs enough readings for a real max
    full = pd.date_range(day.index.min(), day.index.max(), freq='D')
    day = day.reindex(full)                         # gaps become NaN rows so lags stay truly "yesterday"
    day.index.name = 'date'
    return day.reset_index()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv', help='path to cleaned_data.csv (sub-hourly Mumbai observations)')
    ap.add_argument('--out', default=os.path.join('site', 'assets', 'mumbai.json'))
    a = ap.parse_args()

    day = daily_rows(a.csv)
    day['city'], day['lat'], day['lon'] = 'Mumbai', LAT, LON
    day['date'] = day['date'].dt.strftime('%Y-%m-%d')
    day['rain'] = np.nan                            # not in this dataset; the model takes NaN
    day['wind'] = np.nan
    feats = make_features(day)
    rows = feats[feats['tmax'].notna()].reset_index(drop=True)   # a prediction needs today's readings

    model = load_model(os.path.join(MODEL_DIR, 'trained_model.pkl'))
    preds = model.predict(rows[FEATURES].astype(float))

    # Each prediction is FOR the next day; pair it with that day's actual max where one exists.
    for_date = (pd.to_datetime(rows['date']) + pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d')
    actual = rows['target']
    ok = actual.notna()
    mae = float(np.abs(actual[ok] - preds[ok]).mean())
    persistence = float(np.abs(actual[ok] - rows['tmax'][ok]).mean())

    out = {
        'city': 'Mumbai', 'generated_at': datetime.now().isoformat(timespec='minutes'),
        'source': os.path.basename(a.csv), 'start': for_date.iloc[0], 'end': for_date.iloc[-1],
        'days': int(len(rows)), 'scored_days': int(ok.sum()),
        'mae': round(mae, 2), 'persistence_mae': round(persistence, 2),
        'dates': for_date.tolist(),
        'actual': [round(v, 1) if pd.notna(v) else None for v in actual],
        'predicted': [round(float(p), 1) for p in preds],
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f)

    print(f"{len(rows)} days predicted ({out['start']} to {out['end']}), {out['scored_days']} with an actual to compare")
    print(f"mean error {out['mae']} C; carrying today forward {out['persistence_mae']} C")
    print(f"Written to {a.out}")


if __name__ == '__main__':
    main()
