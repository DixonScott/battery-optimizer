import random

import numpy as np
import pandas as pd
import pytest

from battery_optimizer.lp_scheduler import lp_schedule


@pytest.mark.parametrize("seed", list(range(100)))
def test_random_lp_scheduler(seed):
    random.seed(seed)

    # --- Randomize parameters ---
    n = random.randint(12, 48)  # between 6h and 24h when dt = 0.5
    dt = 0.5  # half an hour between timestamps

    max_charge_kw = random.uniform(1,5)
    max_discharge_kw = random.uniform(1, 5)
    min_soc_kwh = 0
    max_soc_kwh = random.uniform(5, 20)
    initial_soc_kwh = random.uniform(min_soc_kwh, max_soc_kwh)
    efficiency = random.uniform(0.6, 0.999)

    # power demand of the home
    power_demand = [
        random.uniform(0, max_discharge_kw * 0.8)  # not too aggressive
        for _ in range(n)
    ]

    # DataFrame of electricity prices and carbon intensity
    hours = pd.date_range("2025-01-01", periods=n, freq="30min")  # freq matches dt
    df = pd.DataFrame({
        "import_price_p_per_kWh": [random.uniform(5, 30) for _ in range(n)],
        "export_price_p_per_kWh": [random.uniform(0, 20) for _ in range(n)],
        "carbon_intensity_g_per_kWh": [random.uniform(100, 400) for _ in range(n)],
    }, index=hours)

    # Random mode
    mode = random.choice(["cost", "carbon"])

    # --- Run LP scheduler ---
    _, _, results_df = lp_schedule(
        df, mode, max_charge_kw, max_discharge_kw,
        min_soc_kwh, max_soc_kwh, initial_soc_kwh, efficiency,
        power_demand
    )

    # Print parameters, results and SoC over time
    print("Seed:", seed)
    print("Mode:", mode)
    print("max_charge_kw:", max_charge_kw)
    print("max_discharge_kw:", max_discharge_kw)
    print("min_soc_kwh:", min_soc_kwh)
    print("max_soc_kwh:", max_soc_kwh)
    print("initial_soc_kwh:", initial_soc_kwh)
    print("efficiency:", efficiency)
    print("power_demand:", power_demand)

    charge = results_df["charge"].to_numpy()
    discharge_home = results_df["discharge_home"].to_numpy()
    discharge_grid = results_df["discharge_grid"].to_numpy()
    grid_home = results_df["grid_home"].to_numpy()
    discharge = discharge_home + discharge_grid
    print(results_df[["charge", "discharge_home", "discharge_grid", "grid_home"]])

    soc = initial_soc_kwh + np.cumsum((efficiency * charge - discharge) * dt)
    soc = np.insert(soc, 0, initial_soc_kwh)
    print("SoC:")
    print(soc)

    # Check for simultaneous charge and discharge
    # Allowed in current version, and occurred in 3.4% of timesteps over 100 tests
    for t in range(n):
        if charge[t] > 0 and discharge[t] > 0:
            print(f"Simultaneous charge/discharge at timestep {t}")

    # --- Assertions ---
    soc = initial_soc_kwh
    for t in range(n):
        c, d, gh, dh = charge[t], discharge[t], grid_home[t], discharge_home[t]

        # Bounds on charge / discharge
        assert 0 <= c <= max_charge_kw + 1e-6
        assert 0 <= d <= max_discharge_kw + 1e-6
        assert gh + dh + 1e-6 >= power_demand[t]  # meet profile requirement

        # SoC within bounds
        soc += (efficiency * c - d) * dt
        assert min_soc_kwh - 1e-6 <= soc <= max_soc_kwh + 1e-6
