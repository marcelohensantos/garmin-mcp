from auth import get_client


def main() -> None:
    print("Connecting to Garmin Connect...")
    client = get_client()

    print(f"  Name:    {client.get_full_name()}")

    for d in client.get_devices():
        print(f"  Device:  {d.get('productDisplayName', 'unknown')}")

    activities = client.get_activities(0, 5)
    print(f"  Recent activities ({len(activities)}):")
    for a in activities:
        print(f"    · {a.get('activityName', '?')}  {a.get('startTimeLocal', '?')}")

    print("\nConnection OK")


if __name__ == "__main__":
    main()
