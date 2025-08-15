import pandas as pd


def simulate_battery(df, schedule=None, capacity_kwh=3.0, initial_soc_kwh=1.0,
                     min_soc_kwh=0.0, max_soc_kwh=None,
                     max_charge_kw=3.5, max_discharge_kw=3.5,
                     efficiency=0.9):
    """
    Simulate a battery's state of charge over time given a charging/discharging schedule.

    Parameters
    ----------
    df : pd.DataFrame
        Must have a DateTimeIndex matching the schedule index.
        Expected columns: import_price_p_per_kWh, export_price_p_per_kWh, carbon_intensity_g_per_kWh.
    schedule : list or None
        Charging/discharging plan in kW (+ means charging, - means discharging) for each timestamp in `df`.
        If None, uses an all-zero schedule.
    capacity_kwh : float
        Total battery capacity in kWh.
    initial_soc_kwh : float
        Starting state of charge in kWh.
    min_soc_kwh : float
        Minimum allowed state of charge in kWh.
    max_soc_kwh : float or None
        Maximum allowed state of charge in kWh. Defaults to `capacity_kwh` if None.
    max_charge_kw : float
        Maximum charging rate in kW.
    max_discharge_kw : float
        Maximum discharging rate in kW.
    efficiency : float
        Round-trip efficiency (0 < efficiency ≤ 1).

    Returns
    -------
    pd.DataFrame
        Original df with added columns: actual_power_kw, soc_kwh.
    """
    if schedule is None:
        schedule = [0] * len(df)
    schedule = pd.Series(schedule, index=df.index)

    if max_soc_kwh is None:
        max_soc_kwh = capacity_kwh

    soc = initial_soc_kwh
    soc_list = []
    actual_power_list = []

    step_hours = (df.index[1] - df.index[0]).total_seconds() / 3600

    for ts, power in schedule.items():
        # Clip requested power to allowed range
        if power > 0:
            power = min(power, max_charge_kw)
            # Adjust for efficiency on charging
            soc_change = power * step_hours * efficiency
        else:
            power = max(power, -max_discharge_kw)
            soc_change = power * step_hours

        # Apply SoC limits
        new_soc = soc + soc_change
        if new_soc > max_soc_kwh:
            # Reduce charging to not exceed max
            soc_change = max_soc_kwh - soc
            power = soc_change / step_hours / (efficiency if power > 0 else 1/efficiency)
            new_soc = max_soc_kwh
        elif new_soc < min_soc_kwh:
            # Reduce discharging to not go below min
            soc_change = min_soc_kwh - soc
            power = soc_change / step_hours / (efficiency if power > 0 else 1/efficiency)
            new_soc = min_soc_kwh

        soc_list.append(soc)
        soc = new_soc
        actual_power_list.append(power)

    df = df.copy()
    df["actual_power_kw"] = actual_power_list
    df["soc_kwh"] = soc_list
    return df
