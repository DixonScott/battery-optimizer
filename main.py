from battery_scheduler.prepare_data import prepare_data


def main():
    df = prepare_data()
    print(df.head(10))


if __name__ == "__main__":
    main()
