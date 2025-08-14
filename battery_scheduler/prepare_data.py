from datetime import datetime, timedelta, UTC

import pandas as pd
import requests

from . import config

# ---------------------------
# BUILD HALF-HOURLY INDEX
# ---------------------------

def build_time_index(hours=48):
    now = datetime.now(UTC)
    # Round to nearest half hour
    minute = 30 if now.minute >= 30 else 0
    now = now.replace(minute=minute, second=0, microsecond=0)
    end = now + timedelta(hours=hours)
    return pd.date_range(start=now, end=end, freq="30min", tz="UTC")

# ---------------------------
# PRICE MODELS
# ---------------------------

def get_flat_prices(index):
    return pd.Series([config.FLAT_IMPORT_PRICE] * len(index), index=index)


def get_tou_prices(index):
    prices = []
    for ts in index:
        hour = ts.hour
        for start, end, price in config.TOU_PERIODS:
            if start <= hour < end:
                prices.append(price)
                break
    return pd.Series(prices, index=index)


def get_csv_prices(index, path):
    df = pd.read_csv(path)

    # Convert 'time' column to timedelta since midnight
    df["time"] = pd.to_timedelta(df["time"] + ":00")

    # Create series to map times to prices
    price_map = pd.Series(df["price"].values, index=df["time"])

    # Extract the time-of-day for each timestamp in the index
    time_of_day = index - index.normalize()

    # Restore the original index with dates
    price_series = price_map.reindex(time_of_day, method="nearest")
    price_series.index = index

    return price_series

# ---------------------------
# CARBON INTENSITY
# ---------------------------

def get_carbon_intensity(index):
    start_str = index[1].strftime("%Y-%m-%dT%H:%MZ")
    end_str = (index.max() + pd.Timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%MZ")
    url = config.CARBON_API_URL.format(from_dt=start_str, to_dt=end_str)
    r = requests.get(url)
    data = r.json()["data"]
    ci_series = pd.Series(
        {pd.to_datetime(d["from"], utc=True): d["intensity"]["forecast"]
         for d in data}
    )
    return ci_series.reindex(index, method="nearest")

# ---------------------------
# MAIN
# ---------------------------

def prepare_data():
    idx = build_time_index(config.FORECAST_HOURS)

    # Prices
    if config.TARIFF_TYPE == "flat":
        import_prices = get_flat_prices(idx)
    elif config.TARIFF_TYPE == "TOU":
        import_prices = get_tou_prices(idx)
    elif config.TARIFF_TYPE == "csv":
        import_prices = get_csv_prices(idx, config.CSV_PATH)
    else:
        raise ValueError("Unknown tariff type")

    export_prices = pd.Series([config.FLAT_EXPORT_PRICE] * len(idx), index=idx)

    # Carbon intensity
    carbon = get_carbon_intensity(idx)

    # Combine into DataFrame
    df = pd.DataFrame({
        "import_price_p_per_kWh": import_prices,
        "export_price_p_per_kWh": export_prices,
        "carbon_intensity_g_per_kWh": carbon
    })
    return df
