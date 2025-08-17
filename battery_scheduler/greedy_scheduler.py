import pandas as pd


def greedy_schedule(df, capacity_kwh=3.0, initial_soc_kwh=1.0,
                    min_soc_kwh=0.0, max_soc_kwh=None,
                    max_charge_kw=3.5, max_discharge_kw=3.5,
                    mode="cost", alpha=0.5,
                    discharge_profile=None):
    """
    Build a greedy charge/discharge schedule.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns:
        - "import_price_p_per_kWh"
        - "export_price_p_per_kWh"
        - "carbon_intensity_g_per_kWh"
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
    mode : {"cost", "carbon", "weighted"}
        Optimisation goal.
    alpha : float
        Weight for cost in weighted mode (0 ≤ alpha ≤ 1).
    discharge_profile : list
        Energy (kwh) required from the battery at each timestep (if physically possible).

    Returns
    -------
    list
        Charging plan in kW (+ charge, - discharge).
    """
    if max_soc_kwh is None:
        max_soc_kwh = capacity_kwh

    schedule = pd.Series(0.0, index=df.index)
    soc = initial_soc_kwh
    dt = (df.index[1] - df.index[0]).total_seconds() / 3600  # hours per timestep

    # Build score series
    if mode == "cost":
        buy_score = df["import_price_p_per_kWh"]
        sell_score = df["import_price_p_per_kWh"]
    elif mode == "carbon":
        buy_score = df["carbon_intensity_g_per_kWh"]
        sell_score = df["carbon_intensity_g_per_kWh"]
    elif mode == "weighted":
        imp_norm = (df["import_price_p_per_kWh"] - df["import_price_p_per_kWh"].min()) / \
                    (df["import_price_p_per_kWh"].max() - df["import_price_p_per_kWh"].min())
        carb_norm = (df["carbon_intensity_g_per_kWh"] - df["carbon_intensity_g_per_kWh"].min()) / \
                    (df["carbon_intensity_g_per_kWh"].max() - df["carbon_intensity_g_per_kWh"].min())
        buy_score = alpha * imp_norm + (1 - alpha) * carb_norm
        sell_score = buy_score
    else:
        raise ValueError("Unknown mode")

    if discharge_profile is None:
        discharge_profile = pd.Series(0.0, index=df.index)
    else:
        discharge_profile = pd.Series(discharge_profile, index=df.index)

    timestep_changed = True

    while timestep_changed:
        timestep_changed = False

        # --- Charge pass ---
        for t in buy_score.sort_values().index:
            if schedule[t] != 0:
                continue  # Skip already scheduled timesteps

            soc = initial_soc_kwh + (schedule[:t] * dt).sum()

            charge_avail = min(max_charge_kw * dt, max_soc_kwh - soc)
            if charge_avail <= 0:
                continue

            if not would_break_soc(schedule, t, charge_avail / dt, initial_soc_kwh, min_soc_kwh, max_soc_kwh, dt):
                schedule[t] += charge_avail / dt
                timestep_changed = True

        # --- Discharge pass ---
        for t in sell_score.sort_values(ascending=False).index:
            if schedule[t] != 0:
                continue  # Skip already scheduled timesteps

            soc = initial_soc_kwh + (schedule[:t] * dt).sum()
            # Discharge what is required by profile unless physically impossible
            discharge_avail = min(max_discharge_kw * dt, soc - min_soc_kwh, discharge_profile[t])
            if discharge_avail <= 0:
                continue

            if not would_break_soc(schedule, t, -discharge_avail / dt, initial_soc_kwh, min_soc_kwh, max_soc_kwh, dt):
                schedule[t] -= discharge_avail / dt
                discharge_profile[t] -= discharge_avail
                timestep_changed = True

        # Stop if SOC is full and mandatory discharge satisfied
        if soc >= max_soc_kwh and discharge_profile.sum() <= 0:
            break

    return schedule.tolist()


def would_break_soc(schedule, t, delta_power, init_soc, min_soc, max_soc, dt):
    """
    Returns True if adding delta_power at timestep t would make SoC
    go outside bounds at any point in the schedule.
    """
    # Copy schedule and add the proposed change
    schedule_copy = schedule.copy()
    schedule_copy[t] += delta_power

    soc = init_soc
    for power in schedule_copy:
        soc += power * dt
        if soc < min_soc or soc > max_soc:
            return True
    return False
