# scripts/weather_reporter.py
"""On-air weather reporter for Indian cities.

Reads live conditions and the last three days from Open-Meteo for twelve cities, works out
what changed, projects where the air over each city is heading on the wind, and has Claude
narrate it like a broadcast correspondent: what changed, why, and which city is next.

Usage, from the project root:
  python -m scripts.weather_reporter                      # Claude narrates (needs ANTHROPIC_API_KEY)
  python -m scripts.weather_reporter --local              # a local model through Ollama (qwen2.5:7b)
  python -m scripts.weather_reporter --local llama3.1:8b  # any model Ollama has pulled
  python -m scripts.weather_reporter --no-llm             # rules-only bulletin, no model call
  python -m scripts.weather_reporter --out path/to/bulletin.json
"""
import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import List, Literal

from pydantic import BaseModel, ValidationError

from src.config import CITIES, RESULTS_DIR

IST = timezone(timedelta(hours=5, minutes=30))
COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
WMO = {0: 'clear sky', 1: 'mainly clear', 2: 'partly cloudy', 3: 'overcast', 45: 'fog', 48: 'fog',
       51: 'drizzle', 53: 'drizzle', 55: 'drizzle', 61: 'light rain', 63: 'rain', 65: 'heavy rain',
       80: 'showers', 81: 'showers', 82: 'heavy showers', 95: 'thunderstorm', 96: 'thunderstorm with hail',
       99: 'thunderstorm with hail'}


def fetch():
    """One Open-Meteo call for every city: current conditions, three past days, two forecast days."""
    names = list(CITIES)
    q = {
        'latitude': ','.join(str(CITIES[n][0]) for n in names),
        'longitude': ','.join(str(CITIES[n][1]) for n in names),
        'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,'
                   'surface_pressure,cloud_cover,weather_code',
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,'
                 'wind_direction_10m_dominant,weather_code',
        'past_days': 3, 'forecast_days': 2, 'timezone': 'Asia/Kolkata',
    }
    url = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    return dict(zip(names, data if isinstance(data, list) else [data]))


def downwind(lat, lon, wind_from_deg, speed_kmh, hours=24):
    """Where the air over a point ends up after `hours`. Wind direction is where it blows FROM."""
    bearing = math.radians((wind_from_deg + 180) % 360)
    d = speed_kmh * hours
    return lat + d * math.cos(bearing) / 111.0, lon + d * math.sin(bearing) / (111.0 * math.cos(math.radians(lat)))


def nearest(lat, lon, exclude):
    best = None
    for name, (la, lo) in CITIES.items():
        if name == exclude:
            continue
        km = math.hypot((la - lat) * 111.0, (lo - lon) * 111.0 * math.cos(math.radians(lat)))
        if best is None or km < best[1]:
            best = (name, round(km))
    return best


assert downwind(20, 75, 270, 10, 1)[1] > 75        # a west wind carries air east
assert nearest(18.6, 73.9, 'Mumbai')[0] == 'Pune'   # nearest city lookup


def observe(raw):
    """Turn the raw feed into one plain record per city, including the 24-hour downwind city."""
    obs = []
    for name, d in raw.items():
        c, day = d['current'], d['daily']
        i = day['time'].index(c['time'][:10])          # today's slot in the daily arrays
        wd, ws = c['wind_direction_10m'], c['wind_speed_10m']
        la, lo = downwind(*CITIES[name], wd, ws)
        nxt = nearest(la, lo, name)
        obs.append({
            'city': name, 'time_ist': c['time'],
            'now': {'temp_c': c['temperature_2m'], 'humidity_pct': c['relative_humidity_2m'],
                    'rain_mm': c['precipitation'], 'wind_kmh': ws, 'wind_from': COMPASS[round(wd / 45) % 8],
                    'wind_from_deg': wd, 'pressure_hpa': c['surface_pressure'], 'cloud_pct': c['cloud_cover'],
                    'sky': WMO.get(c['weather_code'], 'code %s' % c['weather_code'])},
            'today': {'max': day['temperature_2m_max'][i], 'min': day['temperature_2m_min'][i],
                      'rain_mm': day['precipitation_sum'][i]},
            'yesterday': {'max': day['temperature_2m_max'][i - 1], 'min': day['temperature_2m_min'][i - 1],
                          'rain_mm': day['precipitation_sum'][i - 1]},
            'three_day_rain_mm': round(sum(day['precipitation_sum'][max(0, i - 3):i]), 1),
            'tomorrow': {'max': day['temperature_2m_max'][i + 1], 'min': day['temperature_2m_min'][i + 1],
                         'rain_mm': day['precipitation_sum'][i + 1], 'sky': WMO.get(day['weather_code'][i + 1], '')},
            'max_change_vs_yesterday': round(day['temperature_2m_max'][i] - day['temperature_2m_max'][i - 1], 1),
            'downwind_24h': {'nearest_city': nxt[0], 'km_off': nxt[1], 'air_travels_km': round(ws * 24)},
        })
    return obs


def rules_bulletin(obs):
    """A factual bulletin with no model: the numbers, the biggest swings, and the downwind city."""
    wettest = max(obs, key=lambda o: o['now']['rain_mm'] + o['today']['rain_mm'])
    swing = max(obs, key=lambda o: abs(o['max_change_vs_yesterday']))
    changes = []
    for o in obs:
        dm, what = o['max_change_vs_yesterday'], []
        if abs(dm) >= 1.5:
            what.append(f"daytime high {'up' if dm > 0 else 'down'} {abs(dm)} C on yesterday")
        if o['today']['rain_mm'] >= 5:
            what.append(f"{o['today']['rain_mm']} mm of rain today")
        if o['now']['wind_kmh'] >= 20:
            what.append(f"wind at {o['now']['wind_kmh']} km/h from the {o['now']['wind_from']}")
        if what:
            changes.append({'city': o['city'], 'what_changed': '; '.join(what),
                            'why': 'Rules mode gives no cause. Run with a model for the why.'})
    nx = wettest['downwind_24h']
    return {
        'headline': f"{swing['city']} swings {abs(swing['max_change_vs_yesterday'])} C; "
                    f"{wettest['city']} wettest at {wettest['today']['rain_mm']} mm",
        'dateline': obs[0]['time_ist'].replace('T', ' ') + ' IST',
        'on_air': ' '.join(
            f"{o['city']}: {o['now']['temp_c']} C, {o['now']['sky']}, wind {o['now']['wind_kmh']} km/h from the "
            f"{o['now']['wind_from']}, {o['today']['rain_mm']} mm of rain today." for o in obs),
        'changes': changes,
        'next': {'system': f"the rain over {wettest['city']}", 'from_city': wettest['city'],
                 'to_city': nx['nearest_city'], 'eta_hours': 24, 'confidence': 'low',
                 'reason': f"Air over {wettest['city']} moves toward {nx['nearest_city']} on the {wettest['now']['wind_from']} "
                           f"wind, about {nx['air_travels_km']} km in 24 hours. A straight-line estimate, nothing more."},
        'watch': [f"{o['city']}: {o['tomorrow']['sky']}, {o['tomorrow']['rain_mm']} mm expected tomorrow"
                  for o in sorted(obs, key=lambda o: -o['tomorrow']['rain_mm'])[:3]],
        'source': 'rules',
    }


SYSTEM = """You are the on-air weather correspondent for an Indian news channel. You receive a structured feed:
live readings for twelve Indian cities, the last three days, tomorrow's forecast, and for each city a
24-hour downwind projection (where the air over it is heading on the current wind).

Write for a general audience in plain, vivid broadcast English. Rules:
- Use only numbers that are in the feed, and name the city and the reading each claim rests on.
- For every change, give the likely physical cause in one or two sentences: monsoon withdrawal, a sea breeze,
  a western disturbance, thunderstorm outflow, a pressure fall, a wind shift, and so on. Say "likely" where
  the feed cannot prove it.
- For the next location, use the wind direction, the wind speed and the downwind_24h projection. Name the
  city likely to feel the system next, give a time window in hours, and a confidence of low, medium or high
  with the reason. If the winds are too light or too scattered to say, say so and pick the least uncertain case.
- Say plainly when the data cannot support a claim. No sensational words. Times in IST.
- on_air is the spoken script: 150 to 220 words, first person plural, no bullet points, no headings.

Field guide for the JSON you return:
- headline: one line under 12 words, the single biggest story of the day.
- dateline: the date and time the readings were taken, for example "22 September 2026, 17:00 IST". Use the date given as today.
- on_air: the spoken script described above.
- changes: one entry per city that changed. what_changed states the observed change with its numbers. why gives the likely cause.
- next: system names what is moving, for example "the rain over Mumbai". from_city and to_city are city names only, taken
  from the feed, and different from each other. eta_hours is a whole number of hours: start from the 24-hour downwind
  figures in the feed and go longer only when the wind is light. confidence is exactly low, medium or high, never a
  percentage; high only when the wind is steady and above 10 km/h. reason is one or two sentences that cite the wind.
  Give each change its own cause; if several cities share one cause, say what differs between them.
- watch: two or three short lines on what to watch tomorrow."""


class Change(BaseModel):
    city: str
    what_changed: str
    why: str


class Next(BaseModel):
    system: str
    from_city: str
    to_city: str
    eta_hours: int
    confidence: Literal['low', 'medium', 'high']
    reason: str


class Bulletin(BaseModel):
    headline: str
    dateline: str
    on_air: str
    changes: List[Change]
    next: Next
    watch: List[str]


def feed_text(obs):
    """One flat line per city. Small models read this far better than nested JSON, and it is shorter for any model."""
    today = obs[0]['time_ist'][:10]
    tomorrow = (datetime.fromisoformat(today) + timedelta(days=1)).date()
    lines = [f"Today is {today}. Readings taken at {obs[0]['time_ist'][11:]} IST. Tomorrow is {tomorrow}.", '']
    for o in obs:
        n, t, y, m, d = o['now'], o['today'], o['yesterday'], o['tomorrow'], o['downwind_24h']
        lines.append(
            f"{o['city']}: now {n['temp_c']} C, humidity {n['humidity_pct']}%, {n['sky']}, wind {n['wind_kmh']} km/h from the "
            f"{n['wind_from']}, pressure {n['pressure_hpa']} hPa, cloud {n['cloud_pct']}%. Today max {t['max']} C "
            f"(yesterday {y['max']} C, change {o['max_change_vs_yesterday']:+} C), rain today {t['rain_mm']} mm, rain over the "
            f"last 3 days {o['three_day_rain_mm']} mm. Tomorrow max {m['max']} C, min {m['min']} C, {m['sky']}, {m['rain_mm']} mm. "
            f"Air over {o['city']} heads toward {d['nearest_city']} ({d['air_travels_km']} km in 24 h).")
    return '\n'.join(lines)


def repair_next(bulletin, obs):
    """A small model sometimes writes a sentence where a city name belongs. Keep the prediction honest."""
    by = {o['city']: o for o in obs}
    nx = bulletin['next']
    nx['from_city'] = nx['from_city'].strip().rstrip('.')
    nx['to_city'] = nx['to_city'].strip().rstrip('.')
    if nx['from_city'] not in by:
        nx['from_city'] = max(obs, key=lambda o: o['today']['rain_mm'])['city']
    if nx['to_city'] not in by or nx['to_city'] == nx['from_city']:
        src = by[nx['from_city']]
        nx['to_city'] = src['downwind_24h']['nearest_city']
        nx['confidence'] = 'low'
        nx['reason'] = (f"The model named no valid city, so this is the plain downwind estimate: air over {nx['from_city']} "
                        f"moves toward {nx['to_city']} on the {src['now']['wind_from']} wind, about "
                        f"{src['downwind_24h']['air_travels_km']} km in 24 hours.")
        bulletin['repaired'] = True
    nx['eta_hours'] = int(max(1, min(72, nx['eta_hours'])))
    return bulletin


def llm_bulletin(obs, model):
    """Claude, over the API. Needs ANTHROPIC_API_KEY."""
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=model,
        max_tokens=8000,
        system=SYSTEM,
        messages=[{'role': 'user', 'content': feed_text(obs)}],
        output_format=Bulletin,
    )
    if response.stop_reason == 'refusal':
        detail = response.stop_details.explanation if response.stop_details else ''
        raise RuntimeError(f'The model declined this request. {detail}')
    bulletin = response.parsed_output.model_dump()
    bulletin['source'] = model
    return bulletin


def local_bulletin(obs, model, host='http://127.0.0.1:11434'):
    """A local model through Ollama. Same brief, same JSON shape, nothing leaves the machine."""
    body = json.dumps({
        'model': model, 'stream': False,
        'format': Bulletin.model_json_schema(),
        'options': {'temperature': 0.2, 'num_ctx': 8192},   # the feed plus brief is ~2k tokens; the default context would cut it
        'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': feed_text(obs)}],
    }).encode('utf-8')
    req = urllib.request.Request(host + '/api/chat', data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=900) as r:
        reply = json.load(r)
    bulletin = Bulletin.model_validate_json(reply['message']['content']).model_dump()
    bulletin['source'] = 'local:' + model
    return bulletin


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-llm', action='store_true', help='rules-only bulletin, no model call')
    ap.add_argument('--local', nargs='?', const='qwen2.5:7b', metavar='MODEL',
                    help='use a local model through Ollama (default qwen2.5:7b) instead of Claude')
    ap.add_argument('--model', default='claude-opus-5', help='Claude model for the API path')
    ap.add_argument('--out', default=os.path.join(RESULTS_DIR, 'bulletin.json'))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # degree signs survive the Windows console

    obs = observe(fetch())
    if a.no_llm:
        bulletin = rules_bulletin(obs)
    elif a.local:
        try:
            bulletin = repair_next(local_bulletin(obs, a.local), obs)
        except urllib.error.HTTPError as e:
            sys.exit(f'Ollama answered {e.code}. If the model is missing, run: ollama pull {a.local}')
        except urllib.error.URLError:
            sys.exit('Ollama is not running. Start it (the Ollama app, or: ollama serve) and try again.')
        except ValidationError as e:
            sys.exit(f'The local model returned malformed output. Try again, or a larger model.\n{e}')
    else:
        import anthropic
        try:
            bulletin = repair_next(llm_bulletin(obs, a.model), obs)
        except anthropic.AuthenticationError:
            sys.exit('The API rejected the credentials. Check ANTHROPIC_API_KEY.')
        except TypeError as e:  # the SDK raises TypeError when no credential source resolves at all
            if 'authentication' not in str(e).lower():
                raise
            sys.exit('No credentials found. Set ANTHROPIC_API_KEY (or run: ant auth login), or pass --no-llm.')
        except anthropic.RateLimitError as e:
            sys.exit(f"Rate limited. Retry after {e.response.headers.get('retry-after', '60')} seconds.")
        except anthropic.APIStatusError as e:
            sys.exit(f'API error {e.status_code}: {e.message}')
        except anthropic.APIConnectionError:
            sys.exit('Could not reach the API. Check the network connection.')

    bulletin['generated_at'] = datetime.now(IST).isoformat(timespec='minutes')
    bulletin['cities'] = [{'city': o['city'], 'temp_c': o['now']['temp_c'], 'sky': o['now']['sky'],
                           'wind_kmh': o['now']['wind_kmh'], 'wind_from': o['now']['wind_from']} for o in obs]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(bulletin, f, indent=1, ensure_ascii=False)

    print(f"\n{bulletin['headline']}\n{bulletin['dateline']}\n\n{bulletin['on_air']}\n")
    for ch in bulletin['changes']:
        print(f"- {ch['city']}: {ch['what_changed']}\n  why: {ch['why']}")
    nx = bulletin['next']
    print(f"\nNEXT: {nx['system']} -> {nx['to_city']} in about {nx['eta_hours']} h ({nx['confidence']} confidence). {nx['reason']}")
    print(f"\nSource: {bulletin['source']}. Written to {a.out}")


if __name__ == '__main__':
    main()
