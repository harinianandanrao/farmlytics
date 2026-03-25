import os
import json
from flask import Blueprint, jsonify, session, request, send_file, current_app
from flask_login import login_required
from app.processor import process_excel, generate_excel_report
from app.models import UploadRecord
import io

api_bp = Blueprint("api", __name__)


def _get_results():
    filename = session.get("last_upload_file")
    if not filename:
        return None
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        return None
    return process_excel(filepath)


@api_bp.route("/summary")
@login_required
def summary():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data. Please upload a file first."}), 404
    return jsonify(results["summary"])


@api_bp.route("/stores")
@login_required
def stores():
    results = _get_results()
    if not results:
        return jsonify([])
    return jsonify(results["store_names"])


@api_bp.route("/price-compare")
@login_required
def price_compare():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data"}), 404

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search = request.args.get("search", "").strip().lower()
    dept_filter = request.args.get("dept", "").strip()
    tab = request.args.get("tab", "all")  # all, cigs, no_cigs

    if tab == "cigs":
        df = results["with_cigarettes"]
    elif tab == "no_cigs":
        df = results["without_cigarettes"]
    else:
        df = results["merged"]

    if search:
        mask = (
            df["ItemNum"].str.lower().str.contains(search, na=False) |
            df["ItemName"].str.lower().str.contains(search, na=False)
        )
        df = df[mask]

    if dept_filter:
        df = df[df["Dept_ID"].str.lower().str.contains(dept_filter.lower(), na=False)]

    total = len(df)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]

    columns = list(page_df.columns)
    rows = page_df.fillna("PRODUCT MISSING").to_dict(orient="records")

    return jsonify({
        "columns": columns,
        "rows": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })


@api_bp.route("/missing-products")
@login_required
def missing_products():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data"}), 404

    df = results["missing_products"]
    store_names = results["store_names"]
    # compute per-row which stores are missing
    rows = []
    for _, row in df.iterrows():
        missing_stores = []
        for s in store_names:
            import pandas as pd
            import numpy as np
            val = row.get(s)
            if val is None or (isinstance(val, float) and np.isnan(val)):
                missing_stores.append(s)
        rows.append({
            "ItemNum": row["ItemNum"],
            "ItemName": row["ItemName"],
            "Dept_ID": row["Dept_ID"],
            "Missing_In": ", ".join(missing_stores),
            "Missing_Count": len(missing_stores),
        })

    return jsonify({"rows": rows, "total": len(rows)})


@api_bp.route("/missing-by-store")
@login_required
def missing_by_store():
    results = _get_results()
    if not results:
        return jsonify([])
    df = results["missing_by_store"]
    return jsonify(df.to_dict(orient="records"))


@api_bp.route("/price-mismatch")
@login_required
def price_mismatch():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data"}), 404

    df = results["price_mismatch"]
    store_names = results["store_names"]

    import pandas as pd
    rows = []
    for _, row in df.iterrows():
        prices = {}
        for s in store_names:
            val = row.get(s)
            try:
                prices[s] = float(val) if val is not None else None
            except (ValueError, TypeError):
                prices[s] = None
        valid = [v for v in prices.values() if v is not None]
        spread = round(max(valid) - min(valid), 2) if len(valid) >= 2 else 0
        rows.append({
            "ItemNum": row["ItemNum"],
            "ItemName": row["ItemName"],
            "Dept_ID": row["Dept_ID"],
            "Prices": prices,
            "Spread": spread,
            "Recommended": float(row.get("Recommended_Price", 0) or 0),
        })

    rows.sort(key=lambda x: x["Spread"], reverse=True)
    return jsonify({"rows": rows, "total": len(rows)})


@api_bp.route("/chart/store-coverage")
@login_required
def chart_store_coverage():
    """Bar chart: product count per store."""
    results = _get_results()
    if not results:
        return jsonify({})

    import pandas as pd
    store_names = results["store_names"]
    merged_numeric = results["merged_numeric"]
    labels = store_names
    values = []
    for s in store_names:
        count = merged_numeric[s].notna().sum()
        values.append(int(count))

    return jsonify({"labels": labels, "values": values})


@api_bp.route("/chart/dept-distribution")
@login_required
def chart_dept_distribution():
    """Pie chart: product count by department."""
    results = _get_results()
    if not results:
        return jsonify({})

    df = results["merged"]
    dist = df["Dept_ID"].value_counts().head(10)
    return jsonify({"labels": dist.index.tolist(), "values": dist.values.tolist()})


@api_bp.route("/chart/price-spread")
@login_required
def chart_price_spread():
    """Bar chart: top 10 products by price spread."""
    results = _get_results()
    if not results:
        return jsonify({})

    df = results["large_diff"].head(10)
    if df.empty:
        return jsonify({"labels": [], "values": []})

    labels = df["ItemName"].tolist()
    values = df["Price_Spread"].tolist()
    return jsonify({"labels": labels, "values": values})


@api_bp.route("/chart/missing-by-store")
@login_required
def chart_missing_by_store():
    results = _get_results()
    if not results:
        return jsonify({})
    df = results["missing_by_store"]
    return jsonify({"labels": df["Store"].tolist(), "values": df["Missing_Products"].tolist()})


@api_bp.route("/departments")
@login_required
def departments():
    results = _get_results()
    if not results:
        return jsonify([])
    depts = sorted(results["merged"]["Dept_ID"].dropna().unique().tolist())
    return jsonify(depts)


@api_bp.route("/download-report")
@login_required
def download_report():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data"}), 404

    report_bytes = generate_excel_report(results)
    base = os.path.splitext(session.get("last_upload_file", "report").split("_", 1)[-1])[0]
    filename = base + "_Farmlytics_Report.xlsx"

    return send_file(
        io.BytesIO(report_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@api_bp.route("/download-report-csv")
@login_required
def download_report_csv():
    results = _get_results()
    if not results:
        return jsonify({"error": "No data"}), 404

    merged = results["merged"]
    csv_bytes = merged.to_csv(index=False).encode("utf-8")
    base = os.path.splitext(session.get("last_upload_file", "report").split("_", 1)[-1])[0]
    filename = base + "_Farmlytics_Report.csv"

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )
