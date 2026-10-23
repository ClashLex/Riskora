from datetime import date

MAX_DATA_AGE_DAYS = 90


def stale_data_warnings(as_of_dates: list[date], today: date | None = None) -> list[str]:
    today = today or date.today()
    stale_dates = sorted(
        {
            item.isoformat()
            for item in as_of_dates
            if 0 <= (today - item).days and (today - item).days > MAX_DATA_AGE_DAYS
        }
    )
    return [
        f"STALE_DATA: data as of {as_of} exceeds the "
        f"{MAX_DATA_AGE_DAYS}-day prototype freshness threshold."
        for as_of in stale_dates
    ]
