from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from battery_optimizer.lp_scheduler import lp_schedule
from battery_optimizer.prepare_data import get_carbon_intensity
import battery_optimizer.results_analysis as analysis


def get_flat_series(date_range, flat=None):
    if flat is None:
        return pd.Series(0, index=date_range)
    return pd.Series(flat, index=date_range)


def get_import_price_series(profile: str, date_range: pd.DatetimeIndex, flat=None):
    if profile == "Flat":
        return get_flat_series(date_range, flat)
    elif profile == "Peak/Off-Peak":
        return pd.Series([30 if t.hour in range(16,20) else 10 for t in date_range], index=date_range)


def get_export_price_series(profile: str, date_range: pd.DatetimeIndex, flat=None):
    if profile == "Flat":
        return get_flat_series(date_range, flat)


def get_demand_series(profile: str, date_range: pd.DatetimeIndex, flat=None):
    if profile == "Flat":
        return get_flat_series(date_range, flat)
    elif profile == "Evening Peak":
        return pd.Series([2.0 if t.hour in range(17,21) else 0.5 for t in date_range], index=date_range)


hours = pd.date_range(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                           periods=24, freq="1h", tz="Europe/London")
df = pd.DataFrame({
    "import_price_p_per_kWh": get_import_price_series("Flat", hours),
    "export_price_p_per_kWh": get_export_price_series("Flat", hours),
    "power_demand": get_demand_series("Flat", hours),
    "carbon_intensity_g_per_kWh": get_carbon_intensity(hours, 60)
})
df.index.name = "timestep"

st.set_page_config(
    page_title="Battery Optimizer",
    page_icon="⚡",
    layout="wide"
)
st.title("Battery Schedule Optimizer ⚡")

tab_info, tab_input, tab_results = st.tabs(["Info ℹ️", "Input 📝", "Results 📊"])

with tab_info:
    col_info1, col_space, col_info2 = st.columns([6, 1, 5])
    with col_info1:
        st.markdown("""
# Home Battery Optimizer

This app calculates the optimal charging and discharging schedule for a home battery to minimise cost or carbon emissions. This is done using linear programming (LP). At each timestep, the LP solver chooses the best charge and discharge actions for the battery, subject to the constraints imposed by the power demand of the home, and the parameters of the battery. 

## How to Use
1. Click the input tab.
2. Set the optimisation mode in the "Choose Profiles" section.
3. Set the import tariff, export tariff and power demand in the "Choose Profiles" section. They can be edited in three ways: using the select boxes at the top, uploading a csv file, or editing in the data editor. Carbon intensity (the mass of CO2 released to produce one kilowatt-hour of energy) is set automatically by fetching today's carbon intensity from [NESO's carbon intensity API](https://carbonintensity.org.uk/).
    - Note: the fastest way to set up a completely new input would be to select "Flat" in each of the select boxes (except optimisation mode), select appropriate values, and then use the data editor to set the remaining values. You can then download this as a CSV for fast input later.
5. Set the battery parameters.
    - Note: round trip efficiency (RTE) is only applied to charging the battery. This means that battery energy refers to usable energy, or energy that can be extracted from the battery.
6. Click "Run Optimization" at the bottom.
7. Click the results tab.
        """)
    with col_info2:
        st.markdown("""
## Results
From top to bottom, the results tab shows:
1. The carbon and cost savings. Only one of these will be maximised, according to the optimisation mode. These are calculated by subtracting the carbon/cost of the schedule from the carbon/cost if there were no battery. A negative value indicates that this schedule increases the carbon emissions or cost.
2. A graph of power over time for up to four power flows, which can be chosen using the selection box. By default, only "charge", the power from the grid to battery, is selected. The other three power flows are:
    - discharge_home: battery to home
    - discharge_grid: battery to grid
    - grid_home: grid to home
3. A graph of energy stored in the battery over time.        
        """)

with tab_input:
    # --- Two-column layout ---
    col_profiles, col_params = st.columns(2)

    with col_profiles:
        st.subheader("Choose Profiles")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            mode = st.selectbox("Optimization mode", ["carbon", "cost"])
        with col2:
            import_profile = st.selectbox("Import tariff", ["-", "Flat", "Peak/Off-Peak"], index=2)
            if import_profile != "-":
                flat_import = None
                if import_profile == "Flat":
                    flat_import = st.number_input("Flat import tariff (p)", value=10, min_value=0, step=1)
                df["import_price_p_per_kWh"] = get_import_price_series(import_profile, hours, flat=flat_import)
        with col3:
            export_profile = st.selectbox("Export tariff", ["-", "Flat"], index=1)
            if export_profile != "-":
                flat_export = None
                if export_profile == "Flat":
                    flat_export = st.number_input("Flat export tariff (p)", value=5, min_value=0, step=1)
                df["export_price_p_per_kWh"] = get_export_price_series(export_profile, hours, flat=flat_export)
        with col4:
            demand_profile = st.selectbox("Power demand", ["-", "Flat", "Evening Peak"], index=2)
            if demand_profile != "-":
                flat_demand = None
                if demand_profile == "Flat":
                    flat_demand = st.number_input("Flat power demand (kW)", value=1.0, min_value=0.0, step=0.1)
                df["power_demand"] = get_demand_series(demand_profile, hours, flat=flat_demand)

        # --- Upload CSV to populate editor ---
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file:
            df_uploaded = pd.read_csv(uploaded_file)
            expected_cols = ["import_price_p_per_kWh", "export_price_p_per_kWh", "power_demand"]
            if set(df_uploaded.columns) >= set(expected_cols) and len(df_uploaded) == 24:
                for col in expected_cols:
                    df[col] = df_uploaded[col].to_numpy()
                if "carbon_intensity_g_per_kWh" in df_uploaded.columns:
                    df["carbon_intensity_g_per_kWh"] = df_uploaded["carbon_intensity_g_per_kWh"].to_numpy()
                st.success("CSV uploaded successfully. You may edit and re-download from the editor below.")
            else:
                st.error(f"CSV must have exactly 24 rows and at least columns: {expected_cols}")

        with st.expander("Edit data manually (optional)"):
            df = st.data_editor(df, num_rows=24, use_container_width=True, height=241)

    with col_params:
        st.subheader("Battery Parameters")
        efficiency = st.slider("Round-Trip Efficiency", 0.0, 1.0, 0.9)
        st.markdown("#### Power Limits")
        col1, col2 = st.columns(2)
        with col1:
            max_charge_kw = st.number_input("Max Charge Power (kW)", 0.1, 20.0, 3.68, 0.1)
        with col2:
            max_discharge_kw = st.number_input("Max Discharge Power (kW)", 0.1, 20.0, 3.68, 0.1)
        st.markdown("#### Energy Limits")
        max_soc_kwh = 13.5
        col1, col2 = st.columns(2)
        with col1:
            initial_soc_kwh = st.number_input("Initial energy (kWh)", 0.0, 100.0, 5.0, 0.1)
        with col2:
            pass
        col1, col2 = st.columns(2)
        with col1:
            min_soc_kwh = st.number_input("Minimum energy (kWh)", 0.0, max_soc_kwh, 0.0, 0.1)
            min_final_soc_kwh = st.number_input("Minimum final energy (kWh)", min_soc_kwh, max_soc_kwh, initial_soc_kwh, 0.1)
        with col2:
            max_soc_kwh = st.number_input("Maximum energy (kWh)", min_soc_kwh, 100.0, max_soc_kwh, 0.1)
            max_final_soc_kwh = st.number_input("Maximum final energy (kWh)", min_soc_kwh, max_soc_kwh, max_soc_kwh, 0.1)

    # --- Run optimisation ---
    run_button = st.button("Run Optimisation")

    if run_button:
        status, soc_series, results = lp_schedule(
            df=df,
            mode=mode,
            max_charge_kw=max_charge_kw,
            max_discharge_kw=max_discharge_kw,
            min_soc_kwh=min_soc_kwh,
            max_soc_kwh=max_soc_kwh,
            initial_soc_kwh=initial_soc_kwh,
            efficiency=efficiency,
            power_demand=df["power_demand"].tolist(),
            min_final_soc_kwh=min_final_soc_kwh,
            max_final_soc_kwh=max_final_soc_kwh
        )
        st.session_state["status"] = status
        st.session_state["soc"] = soc_series
        st.session_state["results"] = results
        st.session_state["selected_flows"] = ["charge"]

        if status == "Optimal":
            st.success("✅ Optimal solution found! See results tab.")
        else:
            st.warning("⚠️ Infeasible problem.")

with tab_results:
    if "status" in st.session_state:
        st.header("Results")
        results = st.session_state["results"]
        # --- KPIs ---
        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            st.metric(label="🌱 Carbon Saved", value=f"{analysis.carbon_saved(results):.2f} kg CO₂")
        with kpi_col2:
            money = analysis.money_saved(results) / 100
            st.metric(label="💰 Money Saved", value=f"{"-" if money < 0 else ""}£{abs(money):.2f}")

        col1, col2 = st.columns([2,3])
        with col1:
            # Let user pick which lines to show
            flows = ["charge", "discharge_home", "discharge_grid", "grid_home"]
            selected_flows = st.multiselect(
                "Select power flows to display",
                options=flows,
                default=st.session_state.get('selected_flows', ["charge"])
            )

        # --- Plot schedule ---
        t_final = results.index[len(results)-1] + (results.index[1] - results.index[0])
        extra_row = results.iloc[[-1]].copy()
        extra_row.index = [t_final]
        results_ext = pd.concat([results, extra_row])

        # Only keep selected flows
        chart_data = results_ext.reset_index().melt(
            id_vars=["index"],
            value_vars=flows,
            var_name="Power flow",
            value_name="Power"
        )
        chart_data = chart_data[chart_data["Power flow"].isin(selected_flows)]

        # Build chart
        power_chart = (
            alt.Chart(chart_data)
            .mark_line(interpolate="step-after")
            .encode(
                x=alt.X("index:T", title="Time"),
                y=alt.Y("Power:Q", title="Power (kW)"),
                color=alt.Color(
                    'Power flow:N',
                    legend=alt.Legend(
                        labelExpr="""
                        {
                          'charge': 'Charging battery',
                          'discharge_home': 'Battery -> Home',
                          'discharge_grid': 'Battery -> Grid',
                          'grid_home': 'Grid -> Home'
                        }[datum.label]
                        """
                    )
                )
            )
            .properties(title="Optimal power schedules", height=250)
        )

        # --- Plot SoC ---
        soc_series = st.session_state["soc"]
        soc_df = pd.DataFrame({
            "timestep": results_ext.index,
            "SoC_kWh": soc_series.values
        })
        soc_chart = (
            alt.Chart(soc_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("timestep", title="Time"),
                y=alt.Y("SoC_kWh", title="Energy (kWh)"),
                color=alt.value("orange")
            )
            .properties(title="Battery energy level", height=200)
        )

        charts = alt.vconcat(power_chart, soc_chart).resolve_scale(x="shared")
        st.altair_chart(charts, use_container_width=True)

        # --- Download button ---
        csv = results.to_csv(index=True).encode("utf-8")
        st.download_button(
            label="Download Schedule as CSV",
            data=csv,
            file_name="schedule.csv",
            mime="text/csv"
        )
    else:
        st.write("No results to display!")
