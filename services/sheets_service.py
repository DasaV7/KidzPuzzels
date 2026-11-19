import json

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
REQUIRED_HEADERS = ["Question", "OptionA", "OptionB", "OptionC", "Correct", "Category"]


def get_sheets_client():
    """Connect using the same [sheets].service_account secret pattern as HBD_Songs."""
    try:
        raw = st.secrets["sheets"]["service_account"]
        if isinstance(raw, str):
            info = json.loads(raw)
        elif isinstance(raw, dict):
            info = dict(raw)
        else:
            info = {key: raw[key] for key in raw}
        if isinstance(info.get("private_key"), str):
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as exc:
        raise RuntimeError(f"Could not connect to Google Sheets: {exc}") from exc


def get_questions(worksheet_name=None):
    """Read and validate question rows from the configured Google spreadsheet."""
    try:
        sheets_config = st.secrets["sheets"]
        spreadsheet_id = sheets_config["spreadsheet_id"]
        worksheet_name = worksheet_name or sheets_config.get("questions_worksheet", "Questions")
        worksheet = get_sheets_client().open_by_key(spreadsheet_id).worksheet(worksheet_name)
        rows = worksheet.get_all_records()
    except Exception as exc:
        raise RuntimeError(f"Could not read puzzle questions from Google Sheets: {exc}") from exc

    if not rows:
        raise ValueError(f"The '{worksheet_name}' worksheet has no question rows.")
    headers = [str(header).strip() for header in rows[0].keys()]
    missing_headers = [header for header in REQUIRED_HEADERS if header not in headers]
    if missing_headers:
        raise ValueError("Missing Google Sheet columns: " + ", ".join(missing_headers))
    clean_rows = []
    for row_number, raw in enumerate(rows, start=2):
        row = {key: str(raw.get(key, "")).strip() for key in REQUIRED_HEADERS}
        if not any(row.values()):
            continue
        missing_values = [key for key, value in row.items() if not value]
        if missing_values:
            raise ValueError(f"Sheet row {row_number} has empty values in: {', '.join(missing_values)}")
        choices = [row[key].casefold() for key in ("OptionA", "OptionB", "OptionC")]
        if len(set(choices)) != 3:
            raise ValueError(f"Sheet row {row_number} must have three distinct answer options.")
        if row["Correct"].casefold() not in choices:
            raise ValueError(f"Sheet row {row_number}: Correct must match one of the three options.")
        clean_rows.append(row)
    if len(clean_rows) < 10:
        raise ValueError(f"At least 10 valid questions are required; found {len(clean_rows)}.")
    return clean_rows
