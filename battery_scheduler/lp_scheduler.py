import pandas as pd
import pulp


def lp_schedule(df, mode, max_charge_kw, max_discharge_kw,
                min_soc_kwh, max_soc_kwh, initial_soc_kwh,
                efficiency, power_demand,
                min_final_soc_kwh = None, max_final_soc_kwh = None):
    """
    Compute optimal battery charging and discharging schedule with linear programming.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing timestep-level data. Must include:
            - 'import_price_p_per_kWh' if using 'cost' mode
            - 'export_price-p_per_kWh' if using 'cost' mode
            - 'carbon_intensity_g_per_kWh' if using 'carbon' mode
    mode : str
        Optimization mode. Options:
            - 'cost': minimize electricity cost
            - 'carbon': minimize carbon emissions
    max_charge_kw : float
        Maximum charging power of the battery (kW).
    max_discharge_kw : float
        Maximum discharging power of the battery (kW).
    min_soc_kwh : float
        Minimum usable energy to be stored in the battery (kWh).
        At least 0, but you may want a guaranteed reserve of energy.
    max_soc_kwh : float
        Maximum usable energy to be stored in the battery (kWh).
        Usually the usable capacity of the battery.
    initial_soc_kwh : float
        Initial state of charge at the start of the schedule (kWh).
    efficiency : float
        Round-trip efficiency (0 < efficiency ≤ 1).
        Only applied on charging.
    power_demand : list of float
        Power demand of the home at each timestep (kW).
        e.g. power_demand[i] is the power required between the ith and (i+1)th timestep.
    min_final_soc_kwh : float, optional
        The minimum state of charge at the end of the schedule (kWh).
        May be set to None (default), in which case the minimum final SoC is still constrained by `min_soc_kwh`.
    max_final_soc_kwh : float, optional
        The maximum state of charge at the end of the schedule (kWh).
        May be set to None (default), in which case the maximum final SoC is still constrained by `max_soc_kwh`.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by timestep with columns:
        - charge: power from the grid to charge the battery (kW)
        - discharge_home: battery power sent to the home (kW)
        - discharge_grid: battery power sent to the grid (kW)
        - grid_home: power drawn directly from the grid to the home (kW)
    """
    n = len(df)
    dt = (df.index[1] - df.index[0]).total_seconds() / 3600

    # Variables
    charge = pulp.LpVariable.dicts("charge", range(n), lowBound=0, upBound=max_charge_kw)
    discharge_home = pulp.LpVariable.dicts("discharge home", range(n), lowBound=0)
    discharge_grid = pulp.LpVariable.dicts("discharge grid", range(n), lowBound=0)
    grid_home = pulp.LpVariable.dicts("grid to home", range(n), lowBound=0)
    soc = pulp.LpVariable.dicts("soc", range(n+1), lowBound=min_soc_kwh, upBound=max_soc_kwh)

    # Problem
    prob = pulp.LpProblem("BatterySchedule", pulp.LpMinimize)

    # Initial SoC
    prob += soc[0] == initial_soc_kwh

    # Final SoC
    if min_final_soc_kwh is not None:
        prob += soc[n] >= min_final_soc_kwh
    if max_final_soc_kwh is not None:
        prob += soc[n] <= max_final_soc_kwh

    for t in range(n):
        # SoC is equal to previous SoC after charging and discharging
        prob += soc[t+1] == soc[t] + dt * (efficiency * charge[t] - discharge_home[t] - discharge_grid[t])
        # power to home must equal the demand
        prob += discharge_home[t] + grid_home[t] == power_demand[t]
        # battery cannot discharge more than its limit
        prob += discharge_home[t] + discharge_grid[t] <= max_discharge_kw

    # Objective functions
    if mode == "cost":
        prob += pulp.lpSum([
            dt * (charge[t] + grid_home[t]) * df["import_price_p_per_kWh"].iloc[t]
            - dt * discharge_grid[t] * df["export_price_p_per_kWh"].iloc[t]
            for t in range(n)
        ])
    elif mode == "carbon":
        prob += pulp.lpSum([
            dt * (charge[t] + grid_home[t]) * df["carbon_intensity_g_per_kWh"].iloc[t]
            for t in range(n)
        ])

    # Solve
    prob.solve()
    status = pulp.LpStatus[prob.status]
    print("LP status:", status)
    print("Objective value:", pulp.value(prob.objective))

    soc_series = pd.Series(
        [pulp.value(soc[t]) for t in range(n+1)],
        name="SoC"
    )

    # Convert results to df
    results_df = pd.DataFrame({
        "charge": {t: pulp.value(charge[t]) for t in range(n)},
        "discharge_home": {t: pulp.value(discharge_home[t]) for t in range(n)},
        "discharge_grid": {t: pulp.value(discharge_grid[t]) for t in range(n)},
        "grid_home": {t: pulp.value(grid_home[t]) for t in range(n)},
    })
    results_df.index = df.index
    results_df.index.name = "timestep"
    return status, soc_series, pd.concat([df, results_df], axis=1)
