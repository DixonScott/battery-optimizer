from datetime import datetime, timedelta, UTC

import pandas as pd
import requests


CARBON_API_URL = "https://api.carbonintensity.org.uk/intensity/{from_dt}/{to_dt}"

# ---------------------------
# BUILD HALF-HOURLY INDEX
# ---------------------------

def build_time_index(hours=48):
    now = datetime.now(UTC)
    # Round to nearest half hour
    minute = 30 if now.minute >= 30 else 0
    now = now.replace(minute=minute, second=0, microsecond=0)
    end = now + timedelta(hours=hours)
    return pd.date_range(start=now, end=end, freq="30min", tz="Europe/London")

# ---------------------------
# PRICE MODELS
# ---------------------------

def get_flat_prices(index, flat_import_price):
    return pd.Series([flat_import_price] * len(index), index=index)


def get_tou_prices(index, tou_periods):
    prices = []
    for ts in index:
        hour = ts.hour
        for start, end, price in tou_periods:
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

def get_carbon_intensity(index, dt=30):
    index_utc = index.tz_convert("UTC")

    start_str = index_utc[1].strftime("%Y-%m-%dT%H:%MZ")
    end_str = (index_utc.max() + pd.Timedelta(minutes=dt)).strftime("%Y-%m-%dT%H:%MZ")

    url = CARBON_API_URL.format(from_dt=start_str, to_dt=end_str)
    r = requests.get(url)
    data = r.json()["data"]

    ci_series = pd.Series(
        {pd.to_datetime(d["from"], utc=True): d["intensity"]["forecast"]
         for d in data}
    )
    ci_series = ci_series.reindex(index_utc, method="nearest")
    ci_series.index = ci_series.index.tz_convert("Europe/London")
    return ci_series

# ---------------------------
# MAIN
# ---------------------------

def prepare_data(
        forecast_hours=48,
        tariff_type="flat",
        flat_export_price=5.0,
        flat_import_price=30.0,
        tou_periods=((0,6,12),(6,16,30),(16,19,40),(19,24,25)),
        csv_path="prices.csv"
):
    """
    Prepare a DataFrame of electricity prices and carbon intensity for a given tariff.

    Parameters
    ----------
    forecast_hours : int
        Number of hours to forecast (default 48).
    tariff_type : str
        Type of electricity tariff: "flat", "TOU" (time-of-use), or "csv" (default "flat").
    flat_export_price : float
        Export price in pence per kWh (default 5.0).
    flat_import_price : float
        Import price in pence per kWh for flat tariff (default 30.0).
    tou_periods : tuple of tuples
        Time-of-use periods in the format ((start_hour, end_hour, price), ...) (used if tariff_type="TOU").
    csv_path : str
        Path to CSV file with prices (used if tariff_type="csv").

    Returns
    -------
    pd.DataFrame indexed by timestamp, with columns:
        - import_price_p_per_kWh
        - export_price_p_per_kWh
        - carbon_intensity_g_per_kWh
    """
    idx = build_time_index(forecast_hours)

    # Prices
    if tariff_type == "flat":
        import_prices = get_flat_prices(idx, flat_import_price)
    elif tariff_type == "TOU":
        import_prices = get_tou_prices(idx, tou_periods)
    elif tariff_type == "csv":
        import_prices = get_csv_prices(idx, csv_path)
    else:
        raise ValueError("Unknown tariff type")

    export_prices = pd.Series([flat_export_price] * len(idx), index=idx)

    # Carbon intensity
    carbon = get_carbon_intensity(idx)

    # Combine into DataFrame
    df = pd.DataFrame({
        "import_price_p_per_kWh": import_prices,
        "export_price_p_per_kWh": export_prices,
        "carbon_intensity_g_per_kWh": carbon
    })
    return df
