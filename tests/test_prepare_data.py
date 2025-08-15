import pandas as pd

from battery_scheduler.prepare_data import prepare_data


def test_prepare_data():
    df = prepare_data()

    # Basic sanity checks
    assert isinstance(df, pd.DataFrame)
    assert "import_price_p_per_kWh" in df.columns
    assert "export_price_p_per_kWh" in df.columns
    assert "carbon_intensity_g_per_kWh" in df.columns

    # Get function defaults
    forecast_hours = prepare_data.__defaults__[0]
    flat_export_price = prepare_data.__defaults__[2]

    # Check lengths
    assert len(df) == forecast_hours * 2 + 1  # half-hourly index

    # Check export prices are all the same as config
    assert all(df["export_price_p_per_kWh"] == flat_export_price)
