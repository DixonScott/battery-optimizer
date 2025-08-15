import pandas as pd

from battery_scheduler.prepare_data import prepare_data
from battery_scheduler.simulate_battery import simulate_battery


def main():
    df = prepare_data()
    df = simulate_battery(df)
    pd.set_option('display.max_columns', None)
    print(df.head(10))


if __name__ == "__main__":
    main()
