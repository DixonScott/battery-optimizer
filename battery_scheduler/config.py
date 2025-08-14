FORECAST_HOURS = 48       # how far ahead to pull data
TARIFF_TYPE = "csv"       # "flat", "TOU", or "csv"
FLAT_IMPORT_PRICE = 30.0  # p/kWh
FLAT_EXPORT_PRICE = 5.0   # p/kWh

TOU_PERIODS = [
    # start_hour (24h), end_hour, price in p/kWh
    (0, 6, 12.0),   # cheap overnight
    (6, 16, 30.0),  # daytime rate
    (16, 19, 40.0), # peak rate
    (19, 24, 25.0)  # evening rate
]

CSV_PATH = "prices.csv"  # CSV of half-hourly electricity prices (columns: time, price)

CARBON_API_URL = "https://api.carbonintensity.org.uk/intensity/{from_dt}/{to_dt}"
