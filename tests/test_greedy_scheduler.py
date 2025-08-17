import pandas as pd
import pytest

from battery_scheduler.greedy_scheduler import greedy_schedule


@pytest.fixture
def df_cost_test():
    hours = pd.date_range("2024-01-01", periods=48, freq="30min")
    return pd.DataFrame({
        "import_price_p_per_kWh": [10] * 4 + [15] + [10] * 19 + [30] * 24,
        "export_price_p_per_kWh": [5] * 48,
        "carbon_intensity_g_per_kWh": [100] * 48
    }, index=hours)


@pytest.fixture
def df_carbon_test():
    hours = pd.date_range("2024-01-01", periods=48, freq="30min")
    return pd.DataFrame({
        "import_price_p_per_kWh": [10] * 48,
        "export_price_p_per_kWh": [5] * 48,
        "carbon_intensity_g_per_kWh": [100] * 24 + [300] * 24
    }, index=hours)


def test_cost_mode_prefers_cheap_then_expensive(df_cost_test):
    discharge_profile = [0] * 24 + [0.25] * 24
    schedule = greedy_schedule(
        df_cost_test,
        mode="cost",
        max_charge_kw=5,
        max_discharge_kw=5,
        capacity_kwh=10,
        min_soc_kwh=0,
        max_soc_kwh=10,
        initial_soc_kwh=0,
        discharge_profile=discharge_profile
    )
    # Expect: positive charging in cheap half, negative discharging in expensive half
    assert max(schedule[:24]) > 0
    assert min(schedule[24:]) < 0


def test_carbon_mode_prefers_low_then_high(df_carbon_test):
    discharge_profile = [0] * 24 + [0.25] * 24
    schedule = greedy_schedule(
        df_carbon_test,
        mode="carbon",
        max_charge_kw=5,
        max_discharge_kw=5,
        capacity_kwh=10,
        min_soc_kwh=0,
        max_soc_kwh=10,
        initial_soc_kwh=0,
        discharge_profile=discharge_profile
    )
    assert max(schedule[:24]) > 0
    assert min(schedule[24:]) < 0


def test_soc_never_outside_bounds(df_cost_test):
    discharge_profile = [0.125] * 48
    schedule = greedy_schedule(
        df_cost_test,
        mode="cost",
        max_charge_kw=5,
        max_discharge_kw=5,
        capacity_kwh=20,
        min_soc_kwh=2,  # force higher min
        max_soc_kwh=20,
        initial_soc_kwh=5,
        discharge_profile=discharge_profile
    )
    soc = 5
    for power in schedule:
        soc += power * 0.5  # timestamps are half an hour apart
        assert 2 <= soc <= 20


def test_meets_discharge_target(df_cost_test):
    discharge_profile = [0.125] * 48
    schedule = greedy_schedule(
        df_cost_test,
        mode="cost",
        max_charge_kw=5,
        max_discharge_kw=5,
        capacity_kwh=10,
        min_soc_kwh=0,
        max_soc_kwh=10,
        initial_soc_kwh=10,
        discharge_profile=discharge_profile
    )
    total_discharge = -sum(x for x in schedule if x < 0) * 0.5
    expected_discharge = sum(discharge_profile)
    assert total_discharge == expected_discharge
