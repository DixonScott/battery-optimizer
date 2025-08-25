def carbon_saved(df):
    """Calculate carbon saved (kg CO2) compared to no battery."""
    dt = (df.index[1] - df.index[0]).total_seconds() / 3600
    base_carbon = ((df["discharge_home"] + df["grid_home"]) * df["carbon_intensity_g_per_kWh"] * dt).sum()
    carbon = ((df["charge"] + df["grid_home"]) * df["carbon_intensity_g_per_kWh"] * dt).sum()
    return (base_carbon - carbon) / 1000

def money_saved(df):
    """Calculate money saved (pence) compared to no battery."""
    dt = (df.index[1] - df.index[0]).total_seconds() / 3600
    base_money = ((df["discharge_home"] + df["grid_home"]) * df["import_price_p_per_kWh"] * dt).sum()
    money = (((df["charge"] + df["grid_home"]) * df["import_price_p_per_kWh"] - df["discharge_grid"] * df["export_price_p_per_kWh"]) * dt).sum()
    return base_money - money
