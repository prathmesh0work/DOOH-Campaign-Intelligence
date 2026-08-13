import pandas as pd
import numpy as np
from datetime import datetime

POSSIBLE_NAMES = {
    "Campaign_Name":   ["campaign_name", "campaign name", "campaign", "cname", "name"],
    "City":            ["city", "geo_loc", "location", "region", "place"],
    "Industry":        ["industry", "ind_code", "sector", "category", "vertical"],
    "Date":            ["date", "dt_stamp", "day", "period"],
    "revenue":         ["rev_val", "revenue", "income", "sales", "earning"],
    "ad_spend":        ["exp_val", "ad_spend", "spend", "cost", "budget", "expenditure"],
    "Impressions":     ["imp_total", "impressions", "impression", "views", "reach"],
    "Clicks":          ["clk_cnt", "clicks", "click", "taps"],
    "Screen_ID":       ["screen_id", "screen_no", "screen", "display_id", "panel_id", "site_id"],
    "Hours_Booked":    ["hours_booked", "ad_hours", "airtime_hours", "hours_played", "slot_hours", "actual_hours"],
    "Hours_Committed": ["hours_committed", "committed_hours", "contracted_hours", "planned_hours", "expected_hours"],
}

def find_best_match(possible_names, file_columns, lower_columns, already_used):
    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if col_lower == name:
                already_used.add(i); return file_columns[i]
    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if col_lower.startswith(name):
                already_used.add(i); return file_columns[i]
    for name in possible_names:
        for i, col_lower in enumerate(lower_columns):
            if i in already_used:
                continue
            if name in col_lower:
                already_used.add(i); return file_columns[i]
    return None


def find_columns(df, log):
    if df.empty:
        return {}
    file_columns = [col.strip() for col in df.columns]
    lower_columns = [c.lower() for c in file_columns]
    already_used = set()
    column_map = {}
    for field, names in POSSIBLE_NAMES.items():
        match = find_best_match(names, file_columns, lower_columns, already_used)
        column_map[field] = match
        if not match:
            log["warnings"].append(f'could not find a column for "{field}" - will use 0/Unknown')
    return column_map


def parse_number_series(series):
    text = series.astype(str).str.strip().str.lower()
    text = text.replace({"n/a": None, "na": None, "null": None, "-": None, "--": None,
                          "undefined": None, "nil": None, "none": None, "nan": None, "nat": None})
    for symbol in ["₹", "$", "€", "£", ",", "%", " "]:
        text = text.str.replace(symbol, "", regex=False)
    return pd.to_numeric(text, errors="coerce")


def parse_date_series(series):
    text = series.astype(str).str.strip()
    result = pd.Series([None] * len(series), index=series.index, dtype=object)
    remaining = pd.Series(True, index=series.index)

    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"]:
        if not remaining.any():
            break
        parsed = pd.to_datetime(text[remaining], format=fmt, errors="coerce")
        hit_idx = parsed[parsed.notna()].index
        result.loc[hit_idx] = parsed.loc[hit_idx].dt.strftime("%Y-%m-%d")
        remaining.loc[hit_idx] = False

    return result


def clean_text_series(series, default):
    cleaned = series.astype(str).str.strip()
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True)         
    cleaned = cleaned.str.replace(r"[\u2013\u2014]", "-", regex=True)  
    blank = series.isna() | cleaned.isin(["", "nan", "NaT", "None"])
    return cleaned.where(~blank, default)


def get_col(df, column_map, field, fallback):
    col = column_map.get(field)
    return df[col] if col else pd.Series([fallback] * len(df), index=df.index)


def add_calculated_metrics(rows):

    if not rows:
        return rows
    df = pd.DataFrame(rows)
    df["roi_percent"] = np.where(df["ad_spend"] > 0,
        ((df["revenue"] - df["ad_spend"]) / df["ad_spend"] * 100).round(2), 0)
    df["ctr"] = np.where(df["Impressions"] > 0,
        (df["Clicks"] / df["Impressions"] * 100).round(4), 0)
    df["cpc"] = np.where(df["Clicks"] > 0,
        (df["ad_spend"] / df["Clicks"]).round(2), 0)
    df["cpm"] = np.where(df["Impressions"] > 0,
        (df["ad_spend"] / df["Impressions"] * 1000).round(2), 0)
    return df.to_dict("records")


def clean_data(raw_rows):
    log = {
        "total_rows": len(raw_rows), "empty_rows_removed": 0, "duplicate_rows_removed": 0,
        "missing_values_fixed": 0, "invalid_dates": 0, "row_save_to_database": 0,
        "column_map": {}, "warnings": []
    }

    df = pd.DataFrame(raw_rows)
    column_map = find_columns(df, log)

    blank_mask = df.apply(
        lambda row: all(pd.isna(v) or str(v).strip() in ("", "nan", "NaT", "None") for v in row),
        axis=1
    )
    log["empty_rows_removed"] = int(blank_mask.sum())
    df = df[~blank_mask].reset_index(drop=True)

    key = (get_col(df, column_map, "Campaign_Name", "None").astype(str) + "|" +
           get_col(df, column_map, "City", "None").astype(str) + "|" +
           get_col(df, column_map, "Date", "None").astype(str))
    dup_mask = key.duplicated()
    log["duplicate_rows_removed"] = int(dup_mask.sum())
    df = df[~dup_mask].reset_index(drop=True)

    clean = pd.DataFrame(index=df.index)
    clean["Campaign_Name"] = clean_text_series(get_col(df, column_map, "Campaign_Name", None), "Unknown Campaign")
    clean["City"] = clean_text_series(get_col(df, column_map, "City", None), "Unknown")
    clean["Industry"] = clean_text_series(get_col(df, column_map, "Industry", None), "Unknown")
    clean["Screen_ID"] = clean_text_series(get_col(df, column_map, "Screen_ID", None), "Unknown Screen")

    for field in ["revenue", "ad_spend", "Impressions", "Clicks"]:
        numbers = parse_number_series(get_col(df, column_map, field, None))
        log["missing_values_fixed"] += int(numbers.isna().sum())
        clean[field] = numbers.abs().fillna(0)

    for field in ["Hours_Booked", "Hours_Committed"]:
        numbers = parse_number_series(get_col(df, column_map, field, None))
        clean[field] = numbers.abs().fillna(0)

    dates = parse_date_series(get_col(df, column_map, "Date", None))
    log["invalid_dates"] = int(dates.isna().sum())
    clean["Date"] = dates

    clean["roi_percent"] = np.where(clean["ad_spend"] > 0,
        ((clean["revenue"] - clean["ad_spend"]) / clean["ad_spend"] * 100).round(2), 0)
    clean["ctr"] = np.where(clean["Impressions"] > 0,
        (clean["Clicks"] / clean["Impressions"] * 100).round(4), 0)
    clean["cpc"] = np.where(clean["Clicks"] > 0,
        (clean["ad_spend"] / clean["Clicks"]).round(2), 0)
    clean["cpm"] = np.where(clean["Impressions"] > 0,
        (clean["ad_spend"] / clean["Impressions"] * 1000).round(2), 0)

    useless_mask = (clean["revenue"] <= 0) & (clean["Impressions"] <= 0) & (clean["Clicks"] <= 0)
    removed = int(useless_mask.sum())

    if removed:
        log["warnings"].append(f"{removed} rows had zero revenue,impressions and clicks - removed")
    clean = clean[~useless_mask].reset_index(drop=True)

    if log["invalid_dates"] > 0:
        log["warnings"].append(f'{log["invalid_dates"]} rows had a date we could not parse - excluded from date based charts')

    log["final_rows"] = len(clean)
    log["column_map"] = column_map

    return {"rows": clean.to_dict("records"), "log": log}
