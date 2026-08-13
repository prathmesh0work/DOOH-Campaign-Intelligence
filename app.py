import os
import math
import json
import pandas as pd
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
from db_config import fetch_campaigns_from_db,insert_campaigns
from clean_data import clean_data
from dashboard_data import build_dashboard

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  
FRONTEND_FOLDER = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def homepage():
    return send_from_directory(FRONTEND_FOLDER, "index.html")

@app.route("/api/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return json_response({"success": False, "error": "No file provided"}, 400)

        uploaded_file = request.files["file"]

        if not uploaded_file.filename:
            return json_response({"success": False, "error": "No filename"}, 400)

        file_extension = uploaded_file.filename.split(".")[-1].lower()

        if file_extension not in ["csv", "xlsx", "xls"]:
            return json_response({
                "success": False,
                "error": "Please upload a CSV, XLS, or XLSX file."
            }, 400)

        if file_extension == "csv":
            table = pd.read_csv(uploaded_file)
        else:
            table = pd.read_excel(uploaded_file)

        if table.empty:
            return json_response({"success": False, "error": "File is empty."}, 404)

        raw_rows = table.to_dict("records")

        cleaning_result = clean_data(raw_rows)
        clean_rows = cleaning_result["rows"]
        cleaning_log = cleaning_result["log"]

        row_inserted = insert_campaigns(clean_rows)
        cleaning_log["row_save_to_database"] = row_inserted

        dashboard = build_dashboard(clean_rows)

        return json_response({
            "success": True,
            "data": dashboard["rows"],
            "log": cleaning_log,
            "kpis": dashboard["kpis"],
            "charts": dashboard["charts"],
            "tables": dashboard["tables"],
            "insights": dashboard["insights"],
            "filters": dashboard["filters"],
            "has_screen_data": dashboard["has_screen_data"],
            "has_occupancy_data": dashboard["has_occupancy_data"],
            "screens": dashboard["screens"],
            "has_discrepancy_data": dashboard["has_discrepancy_data"],
            "discrepancies": dashboard["discrepancies"],
            "anomalies": dashboard["anomalies"],
        })
    

    except Exception as error:
        return json_response({"success": False, "error": str(error)}, 500)

@app.route("/api/load_from_db",methods=['GET'])
def load_from_db():
    try:
        rows = fetch_campaigns_from_db()
        if not rows:
            return json_response({"success": False, "error": "No data found in Database"},400)
        dashboard = build_dashboard(rows)

        return json_response({
            "success":True,
            "data":dashboard['rows'],
            "log":{"total_rows":len(rows),"final_rows":len(rows),"source":"database"},
            "kpis":dashboard['kpis'],
            "charts":dashboard['charts'],
            "tables":dashboard['tables'],
            "insights":dashboard['insights'],
            "filters":dashboard['filters'],
            "has_screen_data":dashboard['has_screen_data'],
            "has_occupancy_data":dashboard['has_occupancy_data'],
            "screens":dashboard['screens'],
            "has_discrepancy_data":dashboard['has_discrepancy_data'],
            "discrepancies":dashboard['discrepancies'],
            "anomalies":dashboard['anomalies']
        })

    except Exception as error:
        return json_response({"success":False, "error":str(error)}, 500)


@app.route("/api/health", methods=["GET"])
def health_check():
    return json_response({"status": "ok"})

@app.route("/<path:filename>")
def other_files(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)

@app.errorhandler(413)
def file_too_large(error):
    return json_response({
        "success": False,
        "error": "File is too large. Please upload a file under 25MB."
    }, 413)

def make_json_safe(value):
    if isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value

def json_response(data, status_code=200):
    safe_data = make_json_safe(data)
    body = json.dumps(safe_data, ensure_ascii=False, default=str)
    return Response(body, status=status_code, mimetype="application/json")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
