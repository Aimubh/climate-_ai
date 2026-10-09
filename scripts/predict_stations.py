# scripts/predict_stations.py
"""Predict tomorrow's high for every Mumbai station with the trained model.

Same method as scripts/predict_today.py, but the points are Mumbai suburban stations instead of
cities: one Open-Meteo call brings each station's last three days plus today, the model scores
today's feature row per station, and the result is written as JSON for site/mumbai.html.

Usage, from the project root:
  python -m scripts.predict_stations --out site/assets/stations.json
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import pandas as pd
from sklearn.metrics import mean_absolute_error

from scripts.predict_today import week_ahead
from src.config import MODEL_DIR, PROCESSED_DATA_DIR, RESULTS_DIR
from src.data_preprocessing.preprocess import DAILY_FIELDS, FEATURES, make_features
from src.models.model import load_model

IST = timezone(timedelta(hours=5, minutes=30))

# Station -> (latitude, longitude), south to north along each line.
STATIONS = {
    # Western line
    'Churchgate': (18.935, 72.827), 'Marine Lines': (18.946, 72.823), 'Charni Road': (18.952, 72.819),
    'Grant Road': (18.963, 72.816), 'Mumbai Central': (18.969, 72.819), 'Lower Parel': (18.996, 72.830),
    'Dadar': (19.018, 72.843), 'Bandra': (19.054, 72.840), 'Santacruz': (19.081, 72.841),
    'Vile Parle': (19.100, 72.844), 'Andheri': (19.119, 72.846), 'Jogeshwari': (19.136, 72.848),
    'Goregaon': (19.164, 72.849), 'Malad': (19.187, 72.849), 'Kandivali': (19.204, 72.852),
    'Borivali': (19.229, 72.857), 'Dahisar': (19.250, 72.859), 'Mira Road': (19.281, 72.871),
    'Bhayandar': (19.312, 72.852), 'Vasai Road': (19.383, 72.832), 'Virar': (19.456, 72.812),
    # Central line
    'CSMT': (18.940, 72.835), 'Byculla': (18.976, 72.833), 'Sion': (19.046, 72.863),
    'Kurla': (19.065, 72.879), 'Ghatkopar': (19.086, 72.908), 'Vikhroli': (19.111, 72.928),
    'Bhandup': (19.141, 72.937), 'Mulund': (19.172, 72.956), 'Thane': (19.186, 72.975),
    'Dombivli': (19.216, 73.087), 'Kalyan': (19.235, 73.130),
    # Harbour line and Navi Mumbai
    'Wadala': (19.016, 72.858), 'Chembur': (19.062, 72.898), 'Vashi': (19.077, 72.998),
    'Nerul': (19.033, 73.016), 'Belapur': (19.017, 73.040), 'Panvel': (18.990, 73.117),
}


def fetch_recent():
    names = list(STATIONS)
    q = {
        'latitude': ','.join(str(STATIONS[n][0]) for n in names),
        'longitude': ','.join(str(STATIONS[n][1]) for n in names),
        'daily': ','.join(DAILY_FIELDS), 'past_days': 3, 'forecast_days': 8, 'timezone': 'Asia/Kolkata',
    }
    url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    frames = []
    for name, d in zip(names, data if isinstance(data, list) else [data]):
        f = pd.DataFrame({'date': d['daily']['time'], **{col: d['daily'][k] for k, col in DAILY_FIELDS.items()}})
        f.insert(0, 'city', name)
        f.insert(1, 'lat', STATIONS[name][0])
        f.insert(2, 'lon', STATIONS[name][1])
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join(RESULTS_DIR, 'stations.json'))
    a = ap.parse_args()

    model = load_model(os.path.join(MODEL_DIR, 'trained_model.pkl'))
    test = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, 'processed_test_data.csv'))
    mae = mean_absolute_error(test['target'], model.predict(test[FEATURES]))
    persistence = mean_absolute_error(test['target'], test['tmax'])

    recent = make_features(fetch_recent())
    today = datetime.now(IST).date()
    stations = []
    for name in STATIONS:
        f = recent[recent['city'] == name]
        today_max = float(f[f['date'] == today.isoformat()]['tmax'].iloc[0])
        stations.append({'station': name, 'today_max': today_max, 'days': week_ahead(model, f, today)})

    result = {
        'generated_at': datetime.now(IST).isoformat(timespec='minutes'), 'for_date': (today + timedelta(days=1)).isoformat(),
        'test_mae': round(float(mae), 2), 'persistence_mae': round(float(persistence), 2), 'stations': stations,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1)

    print(f"Next seven days, our predicted max by station (tomorrow {result['for_date']} first):")
    print(f"{'station':<16}{'today':>8}  " + ''.join(f"{'+%dd' % (k + 1):>7}" for k in range(7)))
    for s in stations:
        print(f"{s['station']:<16}{s['today_max']:>8.1f}  " + ''.join(f"{d['ours']:>7.1f}" for d in s['days']))
    print(f"\nWritten to {a.out}")


if __name__ == '__main__':
    main()
