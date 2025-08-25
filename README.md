[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
![Last commit](https://img.shields.io/github/last-commit/DixonScott/battery-optimizer)

# Home Battery Optimizer

This app calculates the optimal charging and discharging schedule for a home battery to minimise cost or carbon emissions. This is done using linear programming (LP). At each timestep, the LP solver chooses the best charge and discharge actions for the battery, subject to the constraints imposed by the power demand of the home, and the parameters of the battery. 

## How to Use
1. Click the input tab.
2. Set the optimisation mode in the "Choose Profiles" section.
3. Set the import tariff, export tariff and power demand in the "Choose Profiles" section. They can be edited in three ways: using the select boxes at the top, uploading a csv file, or editing in the data editor. Carbon intensity (the mass of CO2 released to produce one kilowatt-hour of energy) is set automatically by fetching today's carbon intensity from ESO.
    - Note: the fastest way to set up a completely new input would be to select "Flat" in each of the select boxes (except optimisation mode), select appropriate values, and then use the data editor to set the remaining values. You can then download this as a CSV for fast input later.
4. Set the battery parameters.
    - Note: round trip efficiency (RTE) is only applied to charging the battery. This means that battery energy refers to usable energy, or energy that can be extracted from the battery.
5. Click "Run Optimization" at the bottom.
6. Click the results tab.

## Results
From top to bottom, the results tab shows:
1. The carbon and cost savings. Only one of these will be maximised, according to the optimisation mode. These are calculated by subtracting the carbon/cost of the schedule from the carbon/cost if there were no battery. A negative value indicates that this schedule increases the carbon emissions or cost.
2. A graph of power over time for up to four power flows, which can be chosen using the selection box. By default, only "charge", the power from the grid to battery, is selected. The other three power flows are:
    - discharge_home: battery to home
    - discharge_grid: battery to grid
    - grid_home: grid to home
3. A graph of energy stored in the battery over time.

## Limitations/Future Work
- Real-world home batteries do not have this kind of full control over incoming/outgoing power. In this sense, the results show what is theoretically possible. Future work will include new options to make the results representative of the functionality of current home batteries.
- Many battery owners also have a PV system, so integrating power from solar panels would be very useful.
- The timeframe is limited to 24 hours, so it is hard to see at a glance if any savings are substantial. The app would benefit from greater timeframes: week, month and year.
- Carbon intensity data is from the ESO API, which only covers Great Britain.

## Tech Stack
- **Language:** Python
- **Key Libraries:** altair, pandas, PuLP, pytest, requests
- **Web App:** Streamlit

## Run Locally
#### Clone the repository
```
git clone https://github.com/DixonScott/battery-optimizer.git
cd battery-optimizer
```
#### Create and activate virtual environment
```
python -m venv venv
source venv/bin/activate  # On Mac/Linux
venv\Scripts\activate     # On Windows
```
#### Install dependencies
```
pip install -r requirements.txt
```
#### Run the app
```
streamlit run app.py
```

## Acknowledgements
- [Carbon Intesity API](https://carbonintensity.org.uk/) - for carbon intensity data, provided under [Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)