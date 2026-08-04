import pandas as pd
from datetime import datetime

def clean_data(raw_rows):

    log = {
        "total_rows": len(raw_rows),
        "empty_rows_removed": 0,
        "duplicate_rows_removed": 0,
        "missing_values_fixed": 0,
        "invalid_dates": 0,
        "row_save_to_database":0,
        "column_map": {},
        "warnings": []
    }

    column_map = find_columns(raw_rows, log)
    rows = remove_empty_rows(raw_rows, log)
    rows = remove_duplicate_rows(rows, column_map, log)
    rows = clean_every_row(rows, column_map, log)
    rows = add_calculated_metrics(rows)
    rows = remove_useless_rows(rows, log)

    if log["invalid_dates"] > 0:
        log["warnings"].append(
            f'{log["invalid_dates"]} rows had a date we could not parse — those rows are excluded from date-based charts and insights.'
        )

    log["final_rows"] = len(rows)
    log["column_map"] = column_map

    return {"rows": rows, "log": log}

POSSIBLE_NAMES = {
    "Campaign_Name": ["campaign_name", "campaign name", "campaign", "cname", "name"],
    "City":          ["city", "geo_loc", "location", "region", "place"],
    "Industry":      ["industry", "ind_code", "sector", "category", "vertical"],
    "Date":          ["date", "dt_stamp", "day", "period"],
    "revenue":       ["rev_val", "revenue", "income", "sales", "earning"],
    "ad_spend":      ["exp_val", "ad_spend", "spend", "cost", "budget", "expenditure"],
    "Impressions":   ["imp_total", "impressions", "impression", "views", "reach"],
    "Clicks":        ["clk_cnt", "clicks", "click", "taps"],
    "Screen_ID":     ["screen_id", "screen_no", "screen", "display_id", "panel_id", "site_id"],
    "Hours_Booked":  ["hours_booked", "ad_hours", "airtime_hours", "hours_played", "slot_hours", "actual_hours"],
    "Hours_Committed": ["hours_committed", "committed_hours", "contracted_hours", "planned_hours", "expected_hours"],
}


def find_columns(raw_rows, log):
    if not raw_rows:
        return {}

    file_columns = [col.strip() for col in raw_rows[0].keys()]
    lower_columns = [col.lower() for col in file_columns]
    already_used = set()  # indexes of columns already claimed

    column_map = {}

    for field, possible_names in POSSIBLE_NAMES.items():
        match = find_best_match(possible_names, file_columns, lower_columns, already_used)
        column_map[field] = match

        if not match:
            log["warnings"].append(f'Could not find a column for "{field}" — will use 0/Unknown')

    return column_map


def find_best_match(possible_names, file_columns, lower_columns, already_used):

    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if col_lower == name:
                already_used.add(i)
                return file_columns[i]
    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if col_lower.startswith(name):
                already_used.add(i)
                return file_columns[i]

    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if name in col_lower:
                already_used.add(i)
                return file_columns[i]

    return None 

def remove_empty_rows(rows, log):
    kept_rows = []

    for row in rows:
        row_is_empty = True
        for value in row.values():
            if not is_blank(value):
                row_is_empty = False
                break

        if row_is_empty:
            log["empty_rows_removed"] += 1
        else:
            kept_rows.append(row)

    return kept_rows


def is_blank(value):
    """True if a value counts as 'nothing' — None, NaN, empty string, etc."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() in ("", "NaT", "nan", "None")

def remove_duplicate_rows(rows, column_map, log):
    seen_keys = set()
    unique_rows = []

    for row in rows:
        campaign = str(get_value(row, column_map.get("Campaign_Name")))
        city = str(get_value(row, column_map.get("City")))
        date = str(get_value(row, column_map.get("Date")))

        key = campaign + "|" + city + "|" + date

        if key in seen_keys:
            log["duplicate_rows_removed"] += 1
        else:
            seen_keys.add(key)
            unique_rows.append(row)

    return unique_rows


def get_value(row, column_name):
    if not column_name:
        return None
    return row.get(column_name)

def clean_every_row(rows, column_map, log):
    clean_rows = []

    for row in rows:
        new_row = {}
        new_row["Campaign_Name"] = clean_text(get_value(row, column_map.get("Campaign_Name")), "Unknown Campaign")
        new_row["City"] = clean_text(get_value(row, column_map.get("City")), "Unknown")
        new_row["Industry"] = clean_text(get_value(row, column_map.get("Industry")), "Unknown")
        new_row["Screen_ID"] = clean_text(get_value(row, column_map.get("Screen_ID")), "Unknown Screen")

        for field in ["revenue", "ad_spend", "Impressions", "Clicks"]:
            raw_value = get_value(row, column_map.get(field))
            number = parse_number(raw_value)

            if number is None:
                new_row[field] = 0
                log["missing_values_fixed"] += 1
            else:
                new_row[field] = abs(number)

        hours_raw = get_value(row, column_map.get("Hours_Booked"))
        hours_number = parse_number(hours_raw)
        new_row["Hours_Booked"] = abs(hours_number) if hours_number is not None else 0

        committed_raw = get_value(row, column_map.get("Hours_Committed"))
        committed_number = parse_number(committed_raw)
        new_row["Hours_Committed"] = abs(committed_number) if committed_number is not None else 0

        raw_date = get_value(row, column_map.get("Date"))
        new_row["Date"] = parse_date(raw_date)
        if new_row["Date"] is None:
            log["invalid_dates"] += 1

        clean_rows.append(new_row)

    return clean_rows


def clean_text(value, default):
    if is_blank(value):
        return default
    return str(value).strip()


def parse_number(value):
    """Turns almost anything into a number, or None if it really isn't one."""
    if is_blank(value):
        return None

    text = str(value).strip().lower()

    if text in ("n/a", "na", "nil", "none", "null", "-", "--", "undefined"):
        return None

    for symbol in ["₹", "$", "€", "£", ",", "%", " "]:
        text = text.replace(symbol, "")

    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value):
    """Turns a date value (any common format) into a YYYY-MM-DD string."""
    if is_blank(value):
        return None

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()

    formats_to_try = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None 

def add_calculated_metrics(rows):
    for row in rows:
        revenue = row["revenue"]
        spend = row["ad_spend"]
        impressions = row["Impressions"]
        clicks = row["Clicks"]

        if spend > 0:
            row["roi_percent"] = round((revenue - spend) / spend * 100, 2)
        else:
            row["roi_percent"] = 0
        if impressions > 0:
            row["ctr"] = round(clicks / impressions * 100, 4)
        else:
            row["ctr"] = 0
        if clicks > 0:
            row["cpc"] = round(spend / clicks, 2)
        else:
            row["cpc"] = 0
        if impressions > 0:
            row["cpm"] = round(spend / impressions * 1000, 2)
        else:
            row["cpm"] = 0

    return rows

def remove_useless_rows(rows, log):
    useful_rows = []

    for row in rows:
        has_some_data = row["revenue"] > 0 or row["Impressions"] > 0 or row["Clicks"] > 0
        if has_some_data:
            useful_rows.append(row)

    removed_count = len(rows) - len(useful_rows)
    if removed_count > 0:
        log["warnings"].append(f"{removed_count} rows had zero revenue, impressions, and clicks — removed")

    return useful_rows