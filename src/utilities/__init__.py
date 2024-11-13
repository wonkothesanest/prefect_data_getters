from datetime import datetime

# List of possible date formats
date_formats = [
    "%a, %d %b %Y %H:%M:%S %z (%Z)",    # Format with "(UTC)" suffix
    "%a, %d %b %Y %H:%M:%S %z",          # Format without "(UTC)" suffix
    "%Y-%m-%d %H:%M:%S",                 # ISO-style date without timezone
    "%d/%m/%Y %H:%M",                    # European style with day/month/year
    "%b %d, %Y %I:%M %p",                # Month day, year with AM/PM
]

def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except:
        pass
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError("Date format not recognized")



if __name__ == "__main__":
    print(parse_date("2023-06-08T18:13:46.102591Z"))
