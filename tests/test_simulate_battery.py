import pandas as pd

from battery_scheduler import simulate_battery


def test_simulate_battery():
    # 1. Create a minimal dataframe
    index = pd.date_range("2025-08-14 00:00", periods=6, freq="30min")
    df = pd.DataFrame(index=index)

    # 2. Create a simple schedule (+ means charging, - means discharging)
    # Charge 2 kW for first 3 half-hours, then discharge 1 kW for last 3
    schedule = [2, 2, 2, -1, -1, -1]

    # 3. Battery parameters
    capacity_kwh = 3.0  # small for easy verification
    initial_soc_kwh = 1.0  # start at 1 kWh
    max_charge_kw = 2.5
    max_discharge_kw = 1.5
    efficiency = 0.9

    # 4. Run simulation
    result = simulate_battery.simulate_battery(
        df, schedule,
        capacity_kwh=capacity_kwh,
        initial_soc_kwh=initial_soc_kwh,
        max_charge_kw=max_charge_kw,
        max_discharge_kw=max_discharge_kw,
        efficiency=efficiency
    )

    # 5. Compare with expected result
    expected = pd.DataFrame(
        {
            "actual_power_kw": [2.0, 2.0, 4 / 9, -1.0, -1.0, -1.0],
            "soc_kwh": [1.0, 1.9, 2.8, 3.0, 2.5, 2.0]
        },
        index=index
    )

    pd.testing.assert_frame_equal(result, expected)
