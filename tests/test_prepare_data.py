import pandas as pd
from battery_scheduler import prepare_data, config


def test_prepare_data():
    df = prepare_data.prepare_data()

    # Basic sanity checks
    assert isinstance(df, pd.DataFrame)
    assert "import_price_p_per_kWh" in df.columns
    assert "export_price_p_per_kWh" in df.columns
    assert "carbon_intensity_g_per_kWh" in df.columns

    # Check lengths
    assert len(df) == config.FORECAST_HOURS * 2 + 1  # half-hourly index

    # Check export prices are all the same as config
    assert all(df["export_price_p_per_kWh"] == config.FLAT_EXPORT_PRICE)
