import pandas as pd
import numpy as np
import io
import os
from typing import Dict, List, Tuple


CIGARETTE_KEYWORD = "cigarett"
PRICE_DIFF_THRESHOLD = 0.50
MISSING_LABEL = "PRODUCT MISSING"


def load_store_sheets(filepath: str) -> Dict[str, pd.DataFrame]:
    """Load all store sheets (skipping sheet 1 = master pricing)."""
    xl = pd.ExcelFile(filepath)
    sheet_names = xl.sheet_names
    stores = {}

    for name in sheet_names[1:]:  # skip first sheet
        df = xl.parse(name)
        df.columns = [str(c).strip() for c in df.columns]

        # Normalize required columns (case-insensitive match)
        col_map = {}
        for col in df.columns:
            low = col.lower().replace(" ", "").replace("_", "")
            if low in ("itemnum", "barcode", "upc", "sku"):
                col_map[col] = "ItemNum"
            elif low == "itemname":
                col_map[col] = "ItemName"
            elif low in ("dept_id", "deptid", "dept", "department"):
                col_map[col] = "Dept_ID"
            elif low == "price":
                col_map[col] = "Price"

        df = df.rename(columns=col_map)

        required = {"ItemNum", "ItemName", "Dept_ID", "Price"}
        if not required.issubset(set(df.columns)):
            continue  # skip malformed sheets

        df = df[["ItemNum", "ItemName", "Dept_ID", "Price"]].copy()
        df["ItemNum"] = df["ItemNum"].astype(str).str.strip()
        df["ItemName"] = df["ItemName"].astype(str).str.strip()
        df["Dept_ID"] = df["Dept_ID"].astype(str).str.strip()
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna(subset=["ItemNum"])
        df = df[df["ItemNum"] != "nan"]

        stores[name.strip()] = df

    return stores


def build_merged_table(stores: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge all stores into a wide table aligned by ItemNum."""
    all_items = {}

    for store_name, df in stores.items():
        for _, row in df.iterrows():
            key = row["ItemNum"]
            if key not in all_items:
                all_items[key] = {"ItemNum": key, "ItemName": row["ItemName"], "Dept_ID": row["Dept_ID"]}
            all_items[key][store_name] = row["Price"]

    merged = pd.DataFrame(list(all_items.values()))

    store_names = list(stores.keys())
    for s in store_names:
        if s not in merged.columns:
            merged[s] = np.nan

    return merged


def fill_missing_labels(merged: pd.DataFrame, store_names: List[str]) -> pd.DataFrame:
    """Replace NaN store prices with PRODUCT MISSING label."""
    df = merged.copy()
    for s in store_names:
        df[s] = df[s].apply(lambda x: MISSING_LABEL if pd.isna(x) else x)
    return df


def compute_recommended_price(merged: pd.DataFrame, store_names: List[str]) -> pd.Series:
    """Recommended price = max price across stores."""
    numeric_cols = merged[store_names].apply(pd.to_numeric, errors="coerce")
    return numeric_cols.max(axis=1)


def detect_missing_products(merged: pd.DataFrame, store_names: List[str]) -> pd.DataFrame:
    """Return rows where at least one store has a missing product."""
    numeric_cols = merged[store_names].apply(pd.to_numeric, errors="coerce")
    mask = numeric_cols.isna().any(axis=1)
    return merged[mask].copy()


def detect_price_mismatch(merged: pd.DataFrame, store_names: List[str]) -> pd.DataFrame:
    """Return rows where not all store prices are equal (ignoring missing)."""
    numeric_cols = merged[store_names].apply(pd.to_numeric, errors="coerce")
    # only rows with >=2 valid prices
    valid_count = numeric_cols.notna().sum(axis=1)
    max_p = numeric_cols.max(axis=1)
    min_p = numeric_cols.min(axis=1)
    mask = (valid_count >= 2) & (max_p != min_p)
    return merged[mask].copy()


def detect_large_price_diff(merged: pd.DataFrame, store_names: List[str], threshold: float = PRICE_DIFF_THRESHOLD) -> pd.DataFrame:
    """Return rows where max - min price > threshold."""
    numeric_cols = merged[store_names].apply(pd.to_numeric, errors="coerce")
    valid_count = numeric_cols.notna().sum(axis=1)
    spread = numeric_cols.max(axis=1) - numeric_cols.min(axis=1)
    mask = (valid_count >= 2) & (spread > threshold)
    result = merged[mask].copy()
    result["Price_Spread"] = spread[mask].round(2)
    return result.sort_values("Price_Spread", ascending=False)


def segregate_cigarettes(merged: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split into cigarette and non-cigarette products."""
    mask = merged["Dept_ID"].str.lower().str.contains(CIGARETTE_KEYWORD, na=False)
    with_cigs = merged[mask].copy()
    without_cigs = merged[~mask].copy()
    return with_cigs, without_cigs


def missing_by_store(merged: pd.DataFrame, store_names: List[str]) -> pd.DataFrame:
    """Count missing products per store."""
    records = []
    numeric_cols = merged[store_names].apply(pd.to_numeric, errors="coerce")
    for s in store_names:
        missing_count = numeric_cols[s].isna().sum()
        records.append({"Store": s, "Missing_Products": int(missing_count)})
    return pd.DataFrame(records).sort_values("Missing_Products", ascending=False)


def process_excel(filepath: str) -> Dict:
    """Main processing pipeline. Returns all analytics results."""
    stores = load_store_sheets(filepath)
    if not stores:
        raise ValueError("No valid store sheets found. Ensure sheets 2–N have ItemNum, ItemName, Dept_ID, Price columns.")

    store_names = list(stores.keys())
    merged = build_merged_table(stores)

    recommended = compute_recommended_price(merged, store_names)
    merged["Recommended_Price"] = recommended.round(2)

    # Fill missing labels AFTER computing numeric stats
    display_df = fill_missing_labels(merged, store_names)

    missing_prods = detect_missing_products(merged, store_names)
    price_mismatch = detect_price_mismatch(merged, store_names)
    large_diff = detect_large_price_diff(merged, store_names)
    with_cigs, without_cigs = segregate_cigarettes(display_df)
    missing_store_summary = missing_by_store(merged, store_names)

    # Summary stats
    total_products = len(merged)
    total_stores = len(store_names)
    total_missing = int(missing_prods.shape[0])
    total_mismatches = int(price_mismatch.shape[0])

    return {
        "store_names": store_names,
        "merged": display_df,
        "merged_numeric": merged,
        "missing_products": missing_prods,
        "price_mismatch": price_mismatch,
        "large_diff": large_diff,
        "with_cigarettes": with_cigs,
        "without_cigarettes": without_cigs,
        "missing_by_store": missing_store_summary,
        "summary": {
            "total_products": total_products,
            "total_stores": total_stores,
            "total_missing": total_missing,
            "total_mismatches": total_mismatches,
            "total_large_diff": int(large_diff.shape[0]),
        },
    }


def generate_excel_report(results: Dict) -> bytes:
    """Generate manager-friendly Excel report and return as bytes."""
    output = io.BytesIO()
    store_names = results["store_names"]
    merged = results["merged"]
    merged_numeric = results["merged_numeric"]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Formats
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#0B1F3A", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter"
        })
        missing_fmt = workbook.add_format({
            "bg_color": "#FF6B6B", "font_color": "#FFFFFF", "border": 1
        })
        mismatch_fmt = workbook.add_format({
            "bg_color": "#FFD93D", "font_color": "#1A1A1A", "border": 1
        })
        green_fmt = workbook.add_format({
            "bg_color": "#2ECC71", "font_color": "#FFFFFF", "bold": True, "border": 1
        })
        normal_fmt = workbook.add_format({"border": 1})
        number_fmt = workbook.add_format({"border": 1, "num_format": "$#,##0.00"})

        def write_sheet(sheet_name, df, highlight_missing=False, highlight_mismatch_col=None):
            if df.empty:
                df = pd.DataFrame({"Info": ["No data available"]})
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            for col_num, value in enumerate(df.columns):
                ws.write(0, col_num, value, header_fmt)
                ws.set_column(col_num, col_num, max(15, len(str(value)) + 4))
            if highlight_missing:
                for row_num in range(1, len(df) + 1):
                    for col_num, col in enumerate(df.columns):
                        val = df.iloc[row_num - 1, col_num]
                        if str(val) == MISSING_LABEL:
                            ws.write(row_num, col_num, val, missing_fmt)

        # --- Summary sheet ---
        s = results["summary"]
        summary_data = pd.DataFrame([
            {"Metric": "Total Products", "Value": s["total_products"]},
            {"Metric": "Total Stores", "Value": s["total_stores"]},
            {"Metric": "Products with Missing Entries", "Value": s["total_missing"]},
            {"Metric": "Products with Price Mismatches", "Value": s["total_mismatches"]},
            {"Metric": "Products with Large Price Differences (>$0.50)", "Value": s["total_large_diff"]},
            {"Metric": "Stores Analyzed", "Value": ", ".join(store_names)},
        ])
        write_sheet("Summary", summary_data)

        # --- All Products List ---
        all_cols = ["ItemNum", "ItemName", "Dept_ID"] + store_names + ["Recommended_Price"]
        all_products = merged[[c for c in all_cols if c in merged.columns]].copy()
        write_sheet("All_Products_List", all_products, highlight_missing=True)

        # --- With Cigarettes ---
        write_sheet("With_Cigarettes", results["with_cigarettes"], highlight_missing=True)

        # --- Without Cigarettes ---
        write_sheet("Without_Cigarettes", results["without_cigarettes"], highlight_missing=True)

        # --- Price Compare ---
        price_compare = merged_numeric[["ItemNum", "ItemName", "Dept_ID"] + store_names + ["Recommended_Price"]].copy()
        write_sheet("Price_Compare", price_compare)

        # --- Missing Products ---
        write_sheet("Missing_Products", results["missing_products"], highlight_missing=True)

        # --- Missing By Store ---
        write_sheet("Missing_By_Store", results["missing_by_store"])

        # --- Price Mismatch ---
        write_sheet("Price_Mismatch", results["price_mismatch"], highlight_missing=True)

        # --- Top Price Differences ---
        top_diff = results["large_diff"].head(50)
        write_sheet("Top_Price_Differences", top_diff)

        # --- Price Issues (combined) ---
        price_issues = pd.concat([
            results["price_mismatch"].assign(Issue="Price Mismatch"),
            results["large_diff"].assign(Issue="Large Price Diff"),
        ], ignore_index=True).drop_duplicates(subset=["ItemNum"])
        write_sheet("Price_Issues", price_issues, highlight_missing=True)

    output.seek(0)
    return output.read()
