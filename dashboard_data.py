def build_dashboard(rows):
    if not rows:
        return empty_dashboard()

    has_screens = has_screen_data(rows)

    return {
        "rows": rows,
        "campaign_count": len(group_rows_by(rows, "Campaign_Name")),
        "kpis": build_kpis(rows),
        "charts": build_charts(rows),
        "tables": build_tables(rows),
        "insights": build_insights(rows),
        "filters": build_filter_options(rows),
        "has_screen_data": has_screens,
        "has_occupancy_data": has_occupancy_data(rows),
        "screens": build_screen_table(rows) if has_screens else [],
        "has_discrepancy_data": has_discrepancy_data(rows),
        "discrepancies": build_discrepancy_report(rows),
        "anomalies": build_anomaly_report(rows) if has_screens else [],
    }

def has_screen_data(rows):
    for row in rows:
        if row.get("Screen_ID") and row.get("Screen_ID") != "Unknown Screen":
            return True
    return False

def empty_dashboard():
    return {
        "rows": [],
        "campaign_count": 0,
        "kpis": {},
        "charts": {},
        "tables": {"top": [], "bottom": []},
        "insights": [],
        "filters": {},
        "has_screen_data": False,
        "has_occupancy_data": False,
        "screens": [],
        "has_discrepancy_data": False,
        "discrepancies": [],
        "anomalies": [],
    }

def sum_column(rows, field):
    total = 0
    for row in rows:
        total += row.get(field, 0) or 0
    return total

def average_column(rows, field):
    if len(rows) == 0:
        return 0
    return sum_column(rows, field) / len(rows)

def group_rows_by(rows, field):
    groups = {}
    for row in rows:
        key = row.get(field) or "Unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(row)
    return groups

def unique_sorted_values(rows, field):
    values = set()
    for row in rows:
        value = row.get(field)
        if value:
            values.add(value)
    return sorted(values)

def format_number(n):
    n = float(n or 0)

    if n >= 10000000:
        return f"{n / 10000000:.1f}Cr"
    elif n >= 100000:
        return f"{n / 100000:.1f}L"
    elif n >= 1000:
        return f"{n / 1000:.1f}K"
    else:
        return f"{n:.1f}"

def find_best_group(groups, get_metric):
    best_name = ""
    best_value = float("-inf")

    for name, group_rows in groups.items():
        value = get_metric(group_rows)
        if value > best_value:
            best_value = value
            best_name = name

    return {"name": best_name, "value": best_value}

def find_worst_group(groups, get_metric):
    worst_name = ""
    worst_value = float("inf")

    for name, group_rows in groups.items():
        value = get_metric(group_rows)
        if value < worst_value:
            worst_value = value
            worst_name = name

    return {"name": worst_name, "value": worst_value}

def build_kpis(rows):
    return {
        "revenue": format_number(sum_column(rows, "revenue")),
        "impressions": format_number(sum_column(rows, "Impressions")),
        "clicks": format_number(sum_column(rows, "Clicks")),
        "ad_spend": format_number(sum_column(rows, "ad_spend")),
        "roi": f"{average_column(rows, 'roi_percent'):.1f}%",
        "ctr": f"{average_column(rows, 'ctr'):.3f}%",
        "cpc": f"₹{average_column(rows, 'cpc'):.2f}",
        "cpm": f"₹{average_column(rows, 'cpm'):.2f}",
    }

def build_charts(rows):
    charts = {}

    by_date = group_rows_by(rows, "Date")
    dates = sorted(by_date.keys())

    revenue_per_date = [sum_column(by_date[d], "revenue") for d in dates]
    impressions_per_date = [sum_column(by_date[d], "Impressions") for d in dates]

    charts["chartRevTime"] = simple_line_chart(dates, revenue_per_date, "Revenue", "#3b82f6")
    charts["chartImpTime"] = simple_line_chart(dates, impressions_per_date, "Impressions", "#6366f1")

    by_industry = group_rows_by(rows, "Industry")
    industries_sorted = sort_groups_by_revenue(by_industry)
    revenue_per_industry = [sum_column(by_industry[i], "revenue") for i in industries_sorted]
    charts["chartIndustry"] = simple_bar_chart(industries_sorted, revenue_per_industry, "#3b82f6")

    by_city = group_rows_by(rows, "City")
    cities_sorted = sort_groups_by_revenue(by_city)
    revenue_per_city = [sum_column(by_city[c], "revenue") for c in cities_sorted]
    charts["chartCity"] = simple_bar_chart(cities_sorted, revenue_per_city, "#6366f1")

    by_campaign = group_rows_by(rows, "Campaign_Name")
    campaign_summaries = []
    for name, group_rows in by_campaign.items():
        campaign_summaries.append({
            "name": shorten_name(name),
            "roi": average_column(group_rows, "roi_percent"),
            "revenue": sum_column(group_rows, "revenue")
        })

    campaign_summaries.sort(key=by_roi_descending)
    top_10 = campaign_summaries[:10]

    charts["chartRoi"] = {
        "labels": [c["name"] for c in top_10],
        "datasets": [
            {"label": "ROI %", "data": [c["roi"] for c in top_10],
             "backgroundColor": "#475569", "yAxisID": "y"},
            {"label": "Revenue", "data": [c["revenue"] for c in top_10],
             "backgroundColor": "#3b82f6", "yAxisID": "y2"},
        ]
    }

    return charts

def by_roi_descending(campaign):
    return -campaign["roi"]

def sort_groups_by_revenue(groups):
    names = list(groups.keys())
    names.sort(key=lambda name: -sum_column(groups[name], "revenue"))
    return names

def shorten_name(name):
    if len(name) > 22:
        return name[:22] + "…"
    return name

def simple_line_chart(labels, values, label, color):
    return {
        "labels": labels,
        "datasets": [{"label": label, "data": values, "borderColor": color,
                      "backgroundColor": color + "22", "type": "line"}]
    }

def simple_bar_chart(labels, values, color):
    return {
        "labels": labels,
        "datasets": [{"data": values, "backgroundColor": color, "type": "bar"}]
    }

MIN_CAMPAIGNS_TO_SPLIT = 10  

def build_tables(rows):
    by_campaign = group_rows_by(rows, "Campaign_Name")

    summaries = []
    for name, group_rows in by_campaign.items():
        summaries.append({
            "name": name,
            "revenue": sum_column(group_rows, "revenue"),
            "ad_spend": sum_column(group_rows, "ad_spend"),
            "roi": average_column(group_rows, "roi_percent"),
            "ctr": average_column(group_rows, "ctr"),
            "impressions": sum_column(group_rows, "Impressions"),
        })

    summaries.sort(key=lambda c: -c["roi"])  

    if len(summaries) < MIN_CAMPAIGNS_TO_SPLIT:
        return {"top": summaries, "bottom": [], "split": False}

    top_5 = summaries[:5]
    bottom_5 = list(reversed(summaries[-5:])) 

    return {"top": top_5, "bottom": bottom_5, "split": True}

OPERATING_HOURS_PER_DAY = 18

def build_screen_table(rows):
    by_screen = group_rows_by(rows, "Screen_ID")

    screens = []
    for screen_id, group_rows in by_screen.items():
        if screen_id == "Unknown Screen":
            continue 

        revenue = sum_column(group_rows, "revenue")
        impressions = sum_column(group_rows, "Impressions")
        hours_booked = sum_column(group_rows, "Hours_Booked")
        active_days = len(set(r["Date"] for r in group_rows if r.get("Date")))

        hours_available = active_days * OPERATING_HOURS_PER_DAY
        occupancy = round(hours_booked / hours_available * 100, 1) if hours_available > 0 else 0

        screens.append({
            "screen_id": screen_id,
            "city": group_rows[0].get("City", "Unknown"),  
            "revenue": revenue,
            "impressions": impressions,
            "roi": average_column(group_rows, "roi_percent"),
            "ctr": average_column(group_rows, "ctr"),
            "campaign_count": len(set(r["Campaign_Name"] for r in group_rows)),
            "active_days": active_days,
            "hours_booked": hours_booked,
            "occupancy_percent": occupancy,
        })

    screens.sort(key=lambda s: -s["revenue"])

    return screens

def has_occupancy_data(rows):
    """True if at least one row actually had real Hours_Booked data (not 0)."""
    for row in rows:
        if row.get("Hours_Booked", 0) > 0:
            return True
    return False

DISCREPANCY_THRESHOLD_PERCENT = 10

def has_discrepancy_data(rows):
    """True if at least one row has real Hours_Committed data (not 0)."""
    for row in rows:
        if row.get("Hours_Committed", 0) > 0:
            return True
    return False

def build_discrepancy_report(rows):
    if not has_discrepancy_data(rows):
        return []

    flagged = []

    for row in rows:
        committed = row.get("Hours_Committed", 0)
        delivered = row.get("Hours_Booked", 0)

        if committed <= 0:
            continue 

        gap_percent = round((committed - delivered) / committed * 100, 1)

        if gap_percent >= DISCREPANCY_THRESHOLD_PERCENT:
            flagged.append({
                "screen_id": row.get("Screen_ID", "Unknown Screen"),
                "campaign": row.get("Campaign_Name", "Unknown"),
                "city": row.get("City", "Unknown"),
                "date": row.get("Date", ""),
                "hours_committed": committed,
                "hours_delivered": delivered,
                "gap_percent": gap_percent,
            })

    flagged.sort(key=lambda f: -f["gap_percent"]) 
    return flagged

ANOMALY_DROP_THRESHOLD = 0.5

MIN_ACTIVE_DAYS_TO_JUDGE = 3

def build_anomaly_report(rows):
    by_screen = group_rows_by(rows, "Screen_ID")
    anomalies = []

    for screen_id, screen_rows in by_screen.items():
        if screen_id == "Unknown Screen":
            continue
        by_date = group_rows_by(screen_rows, "Date")

        daily_totals = {}
        for day, day_rows in by_date.items():
            if day: 
                daily_totals[day] = sum_column(day_rows, "Impressions")

        if len(daily_totals) < MIN_ACTIVE_DAYS_TO_JUDGE:
            continue  

        average_daily = sum(daily_totals.values()) / len(daily_totals)
        if average_daily <= 0:
            continue

        city = screen_rows[0].get("City", "Unknown")

        for day, actual in daily_totals.items():
            if actual < average_daily * ANOMALY_DROP_THRESHOLD:
                drop_percent = round((average_daily - actual) / average_daily * 100, 1)
                anomalies.append({
                    "screen_id": screen_id,
                    "city": city,
                    "date": day,
                    "impressions": actual,
                    "screen_average": round(average_daily, 1),
                    "drop_percent": drop_percent,
                })

    anomalies.sort(key=lambda a: -a["drop_percent"]) 
    return anomalies

def build_insights(rows):
    by_city = group_rows_by(rows, "City")
    by_industry = group_rows_by(rows, "Industry")
    by_campaign = group_rows_by(rows, "Campaign_Name")

    top_city = find_best_group(by_city, lambda r: sum_column(r, "revenue"))
    top_industry = find_best_group(by_industry, lambda r: sum_column(r, "revenue"))
    top_roi_campaign = find_best_group(by_campaign, lambda r: average_column(r, "roi_percent"))
    worst_roi_campaign = find_worst_group(by_campaign, lambda r: average_column(r, "roi_percent"))
    top_ctr_campaign = find_best_group(by_campaign, lambda r: average_column(r, "ctr"))

    total_revenue = sum_column(rows, "revenue")
    total_spend = sum_column(rows, "ad_spend")
    overall_roi = round((total_revenue - total_spend) / total_spend * 100, 1) if total_spend > 0 else 0

    return [
        {"label": "Top City",
         "text": f"{top_city['name']} generated the highest revenue of ₹{format_number(top_city['value'])}."},
        {"label": "Top Industry",
         "text": f"{top_industry['name']} leads all industries with ₹{format_number(top_industry['value'])} revenue."},
        {"label": "Best ROI Campaign",
         "text": f'"{top_roi_campaign["name"]}" has the best ROI at {top_roi_campaign["value"]:.1f}%.'},
        {"label": "Lowest ROI",
         "text": f'"{worst_roi_campaign["name"]}" has the lowest ROI at {worst_roi_campaign["value"]:.1f}% — review spend.'},
        {"label": "Best CTR Campaign",
         "text": f'"{top_ctr_campaign["name"]}" drives the highest CTR at {top_ctr_campaign["value"]:.3f}%.'},
        {"label": "Overall ROI",
         "text": f"Portfolio ROI across all campaigns: {overall_roi}%."},
    ]

def build_filter_options(rows):
    dates = sorted([row.get("Date") for row in rows if row.get("Date")])

    return {
        "cities": unique_sorted_values(rows, "City"),
        "industries": unique_sorted_values(rows, "Industry"),
        "campaigns": unique_sorted_values(rows, "Campaign_Name"),
        "dates": {
            "min": dates[0] if dates else "",
            "max": dates[-1] if dates else ""
        }
    }
