# Climate AI

Next-day temperature forecasts for twelve Indian cities, built from real daily readings, with a
weather reporter that explains what changed and why, and a website that shows all of it live.

Three parts, one repository:

| Part | What it does | Where |
|---|---|---|
| Pipeline | Fetches 11 years of daily history, trains a model, evaluates it on a held-out year, scores today | `scripts/`, `src/` |
| Reporter | Reads the live feed and writes an on-air bulletin: what changed, the likely cause, and which city the weather reaches next | `scripts/weather_reporter.py` |
| Site | Scroll-driven page with live readings, hold-to-forecast, the bulletin, and a chat with the reporter | `site/` |

## Quick start

```bash
git clone https://github.com/Aimubh/climate-_ai.git
cd climate-_ai
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Run the pipeline from the project root. Every script is a module, so use `python -m`:

```bash
python -m scripts.fetch_weather        # real daily history for 12 cities since 2015, from Open-Meteo
python -m scripts.train_model          # gradient-boosted trees on next-day max temperature
python -m scripts.evaluate_model       # MSE and R2 on the held-out last 365 days
python -m scripts.predict_today --out site/assets/forecast.json     # tomorrow's estimate per city
```

Then the reporter, in one of three modes:

```bash
python -m scripts.weather_reporter --local  --out site/assets/bulletin.json   # local model through Ollama
python -m scripts.weather_reporter          --out site/assets/bulletin.json   # Claude, needs ANTHROPIC_API_KEY
python -m scripts.weather_reporter --no-llm --out site/assets/bulletin.json   # numbers only, no model
```

And the site:

```bash
cd site && python -m http.server 8090
```

Open `http://127.0.0.1:8090/`. Double-clicking `site/index.html` also works.

## What the model is

- **Data:** Open-Meteo's archive, daily values for New Delhi, Jaipur, Lucknow, Ahmedabad, Bhopal, Kolkata,
  Nagpur, Mumbai, Pune, Hyderabad, Chennai and Bengaluru, from 2015-01-01 to yesterday. About 51,000 city-days.
- **Target:** the next day's maximum temperature.
- **Features (19):** the day's max, min and mean temperature, humidity, rain, wind speed and direction, pressure,
  three days of temperature lags, the day-on-day temperature and pressure change, day of year, latitude and longitude.
- **Model:** `HistGradientBoostingRegressor` from scikit-learn. About 1 MB on disk.
- **Split:** time-ordered. The last 365 days are never seen in training.
- **Result** on the held-out year: mean absolute error **0.92 °C**, against **1.02 °C** for simply carrying today's
  high forward. The site prints both numbers under every forecast.

Today's row for live scoring comes from the forecast feed, so the last hours of "today" are the feed's
estimate rather than observation. That is the honest limit of forecasting before the day ends.

## The reporter

`scripts/weather_reporter.py` pulls live conditions and three days of history for the twelve cities, works out
what changed, projects where the air over each city goes in 24 hours on the current wind, and asks a language
model to narrate it as a broadcast correspondent. The reply is validated JSON: headline, spoken script, changes with
causes, the next city with a time window and confidence, and a watch list.

- `--local` uses a model on your own machine through [Ollama](https://ollama.com) (default `qwen2.5:7b`, about 4.7 GB).
  Nothing leaves the machine. About one minute per bulletin on a small GPU.
- Without a flag it uses Claude Opus 5 over the Anthropic API. Set `ANTHROPIC_API_KEY`.
- `--no-llm` writes a rules-only bulletin with the numbers and the downwind city, no cause.

A small guard checks the predicted cities against the feed and repairs the prediction if a model puts anything but a
known city name there. The site labels which model wrote each bulletin.

## The site

`site/index.html` plus `site/assets/`. Plain HTML, CSS and JavaScript, no build step. Live readings and the seven-day
cards come from Open-Meteo in the browser. The model's estimate and the bulletin come from the two JSON files the
scripts write. The "Ask the reporter" chat talks to Ollama on the same machine; on a public host the button stays hidden.

`site-review/` holds the design package and a headless Chrome self-test (`node test.mjs`, no dependencies) that
screenshots the page at desktop and phone sizes, runs the caption flick test and contrast audit, exercises the hold
button, the form and the chat, and checks for console errors.

## Data sources

- [Open-Meteo](https://open-meteo.com): current conditions, forecasts and the historical archive. Free, no key.
- India Meteorological Department station data is the intended next source. Its public site exposes a JSON feed
  for 1,729 stations; its official API at api.imd.gov.in needs permission from IMD.

## Credits

Started from [jmrashed/ai-climate-prediction](https://github.com/jmrashed/ai-climate-prediction) (MIT), whose project
layout and script skeletons this repository keeps. Everything that runs today was built on top of that scaffold.

## License

MIT, see [LICENSE](LICENSE).
