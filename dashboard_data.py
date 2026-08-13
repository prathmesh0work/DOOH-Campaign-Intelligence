import pandas as pd
import numpy as np


def build_dashboard(rows):
    if not rows:
        return empty_dashboard()

    df = pd.DataFrame(rows)
    has_screens = has_screen_data(df)

    return {
        "rows": rows,
        "campaign_count": int(df["Campaign_Name"].nunique()),
        "kpis": build_kpis(df),
        "charts": build_charts(df),
        "tables": build_tables(df),
        "insights": build_insights(df),
        "filters": build_filter_options(df),
        "has_screen_data": has_screens,
        "has_occupancy_data": has_occupancy_data(df),
        "screens": build_screen_table(df) if has_screens else [],
        "has_discrepancy_data": has_discrepancy_data(df),
        "discrepancies": build_discrepancy_report(df),
        "anomalies": build_anomaly_report(df) if has_screens else [],
    }


def has_screen_data(df):
    return bool(((df["Screen_ID"].notna()) & (df["Screen_ID"] != "Unknown Screen")).any())


def empty_dashboard():
    return {
        "rows": [], "campaign_count": 0, "kpis": {}, "charts": {},
        "tables": {"top": [], "bottom": []}, "insights": [], "filters": {},
        "has_screen_data": False, "has_occupancy_data": False, "screens": [],
        "has_discrepancy_data": False, "discrepancies": [], "anomalies": [],
    }


def format_number(n):
    n = float(n or 0)
    if n >= 10000000: return f"{n/10000000:.1f}Cr"
    if n >= 100000: return f"{n/100000:.1f}L"
    if n >= 1000: return f"{n/1000:.1f}K"
    return f"{n:.1f}"


def build_kpis(df):
    return {
        "revenue": format_number(df["revenue"].sum()),
        "impressions": format_number(df["Impressions"].sum()),
        "clicks": format_number(df["Clicks"].sum()),
        "ad_spend": format_number(df["ad_spend"].sum()),
        "roi": f"{df['roi_percent'].mean():.1f}%",
        "ctr": f"{df['ctr'].mean():.3f}%",
        "cpc": f"₹{df['cpc'].mean():.2f}",
        "cpm": f"₹{df['cpm'].mean():.2f}",
    }


def simple_line_chart(labels, values, label, color):
    return {"labels": labels, "datasets": [{"label": label, "data": values,
            "borderColor": color, "backgroundColor": color + "22", "type": "line"}]}


def simple_bar_chart(labels, values, color):
    return {"labels": labels, "datasets": [{"data": values, "backgroundColor": color, "type": "bar"}]}


def shorten_name(name):
    return name[:22] + "…" if len(name) > 22 else name


def build_charts(df):
    charts = {}

    date_for_grouping = df["Date"].fillna("Unknown")
    by_date = df.assign(_date=date_for_grouping).groupby("_date").agg(
        revenue=("revenue", "sum"), Impressions=("Impressions", "sum")
    ).sort_index()
    charts["chartRevTime"] = simple_line_chart(list(by_date.index), by_date["revenue"].tolist(), "Revenue", "#3b82f6")
    charts["chartImpTime"] = simple_line_chart(list(by_date.index), by_date["Impressions"].tolist(), "Impressions", "#6366f1")

    by_industry = df.groupby("Industry")["revenue"].sum().sort_values(ascending=False)
    charts["chartIndustry"] = simple_bar_chart(list(by_industry.index), by_industry.tolist(), "#3b82f6")

    by_city = df.groupby("City")["revenue"].sum().sort_values(ascending=False)
    charts["chartCity"] = simple_bar_chart(list(by_city.index), by_city.tolist(), "#6366f1")

    by_campaign = df.groupby("Campaign_Name").agg(roi=("roi_percent", "mean"), revenue=("revenue", "sum"))
    by_campaign = by_campaign.sort_values("roi", ascending=False).head(10)
    charts["chartRoi"] = {
        "labels": [shorten_name(n) for n in by_campaign.index],
        "datasets": [
            {"label": "ROI %", "data": by_campaign["roi"].round(2).tolist(), "backgroundColor": "#475569", "yAxisID": "y"},
            {"label": "Revenue", "data": by_campaign["revenue"].tolist(), "backgroundColor": "#3b82f6", "yAxisID": "y2"},
        ]
    }
    return charts


MIN_CAMPAIGNS_TO_SPLIT = 10

def build_tables(df):
    summary = df.groupby("Campaign_Name").agg(
        revenue=("revenue", "sum"), ad_spend=("ad_spend", "sum"),
        roi=("roi_percent", "mean"), ctr=("ctr", "mean"), impressions=("Impressions", "sum")
    ).reset_index().rename(columns={"Campaign_Name": "name"})
    summary = summary.sort_values("roi", ascending=False)
    records = summary.to_dict("records")

    if len(records) < MIN_CAMPAIGNS_TO_SPLIT:
        return {"top": records, "bottom": [], "split": False}

    top_5 = records[:5]
    bottom_5 = list(reversed(records[-5:]))
    return {"top": top_5, "bottom": bottom_5, "split": True}


OPERATING_HOURS_PER_DAY = 18

def build_screen_table(df):
    df = df[df["Screen_ID"] != "Unknown Screen"]
    if df.empty:
        return []

    screens = []
    for screen_id, g in df.groupby("Screen_ID"):
        active_days = int(g["Date"].dropna().nunique())
        hours_available = active_days * OPERATING_HOURS_PER_DAY
        hours_booked = g["Hours_Booked"].sum()
        occupancy = round(hours_booked / hours_available * 100, 1) if hours_available > 0 else 0

        screens.append({
            "screen_id": screen_id,
            "city": g["City"].iloc[0] if not g.empty else "Unknown",
            "revenue": g["revenue"].sum(),
            "impressions": g["Impressions"].sum(),
            "roi": g["roi_percent"].mean(),
            "ctr": g["ctr"].mean(),
            "campaign_count": int(g["Campaign_Name"].nunique()),
            "active_days": active_days,
            "hours_booked": hours_booked,
            "occupancy_percent": occupancy,
        })

    screens.sort(key=lambda s: -s["revenue"])
    return screens


def has_occupancy_data(df):
    return bool((df["Hours_Booked"] > 0).any())


DISCREPANCY_THRESHOLD_PERCENT = 10

def has_discrepancy_data(df):
    return bool((df["Hours_Committed"] > 0).any())


def build_discrepancy_report(df):
    if not has_discrepancy_data(df):
        return []

    d = df[df["Hours_Committed"] > 0].copy()
    d["gap_percent"] = ((d["Hours_Committed"] - d["Hours_Booked"]) / d["Hours_Committed"] * 100).round(1)
    flagged = d[d["gap_percent"] >= DISCREPANCY_THRESHOLD_PERCENT].sort_values("gap_percent", ascending=False)

    return [{
        "screen_id": r["Screen_ID"], "campaign": r["Campaign_Name"], "city": r["City"],
        "date": r["Date"] if pd.notna(r["Date"]) else "",   # matches original's row.get("Date","") default
        "hours_committed": r["Hours_Committed"], "hours_delivered": r["Hours_Booked"],
        "gap_percent": r["gap_percent"],
    } for _, r in flagged.iterrows()]


ANOMALY_DROP_THRESHOLD = 0.5
MIN_ACTIVE_DAYS_TO_JUDGE = 3

def build_anomaly_report(df):
    df = df[df["Screen_ID"] != "Unknown Screen"]
    anomalies = []

    for screen_id, g in df.groupby("Screen_ID"):
        daily = g.dropna(subset=["Date"]).groupby("Date")["Impressions"].sum()
        if len(daily) < MIN_ACTIVE_DAYS_TO_JUDGE:
            continue
        average_daily = daily.mean()
        if average_daily <= 0:
            continue
        city = g["City"].iloc[0]

        low_days = daily[daily < average_daily * ANOMALY_DROP_THRESHOLD]
        for day, actual in low_days.items():
            drop_percent = round((average_daily - actual) / average_daily * 100, 1)
            anomalies.append({
                "screen_id": screen_id, "city": city, "date": day, "impressions": actual,
                "screen_average": round(average_daily, 1), "drop_percent": drop_percent,
            })

    anomalies.sort(key=lambda a: -a["drop_percent"])
    return anomalies


def build_insights(df):
    total_revenue = df["revenue"].sum()
    total_spend = df["ad_spend"].sum()
    overall_roi = round((total_revenue - total_spend) / total_spend * 100, 1) if total_spend > 0 else 0

    rev_by_city = df.groupby("City")["revenue"].sum()
    top_city, top_city_val = rev_by_city.idxmax(), rev_by_city.max()

    rev_by_industry = df.groupby("Industry")["revenue"].sum()
    top_industry, top_industry_val = rev_by_industry.idxmax(), rev_by_industry.max()

    roi_by_campaign = df.groupby("Campaign_Name")["roi_percent"].mean()
    top_roi_name, top_roi_val = roi_by_campaign.idxmax(), roi_by_campaign.max()
    worst_roi_name, worst_roi_val = roi_by_campaign.idxmin(), roi_by_campaign.min()

    ctr_by_campaign = df.groupby("Campaign_Name")["ctr"].mean()
    top_ctr_name, top_ctr_val = ctr_by_campaign.idxmax(), ctr_by_campaign.max()

    return [
        {"label": "Top City", "text": f"{top_city} generated the highest revenue of ₹{format_number(top_city_val)}."},
        {"label": "Top Industry", "text": f"{top_industry} leads all industries with ₹{format_number(top_industry_val)} revenue."},
        {"label": "Best ROI Campaign", "text": f'"{top_roi_name}" has the best ROI at {top_roi_val:.1f}%.'},
        {"label": "Lowest ROI", "text": f'"{worst_roi_name}" has the lowest ROI at {worst_roi_val:.1f}% — review spend.'},
        {"label": "Best CTR Campaign", "text": f'"{top_ctr_name}" drives the highest CTR at {top_ctr_val:.3f}%.'},
        {"label": "Overall ROI", "text": f"Portfolio ROI across all campaigns: {overall_roi}%."},
    ]


def build_filter_options(df):
    dates = df["Date"].dropna().sort_values()
    return {
        "cities": sorted(df["City"].dropna().unique().tolist()),
        "industries": sorted(df["Industry"].dropna().unique().tolist()),
        "campaigns": sorted(df["Campaign_Name"].dropna().unique().tolist()),
        "dates": {
            "min": dates.iloc[0] if len(dates) else "",
            "max": dates.iloc[-1] if len(dates) else "",
        }
    }
