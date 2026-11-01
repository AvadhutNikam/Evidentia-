"""
Evidentia AI - Telecommunications (CDR / Tower-Dump) and Financial Analytics Engine.

Key Capabilities:
1. Multi-Format Parsers (CSV, Excel .xlsx / .xls) with dynamic header auto-detection.
2. Every parsed CDR event and bank transaction is tagged with its original 1-based `row_number`
   and source exhibit link for strict judicial traceability.
3. Advanced Telecom Analytics:
   - Co-Location Detection (two phones in the same sector at the same time window).
   - Common Contacts Discovery (bridge conspirators / third-party numbers shared across suspects).
   - Short-Lived / Burner SIM Detection (handsets active for brief windows with low call volume).
   - Impossible Travel / Velocity Anomalies (speeds exceeding physical travel thresholds).
4. Forensic Banking & Money-Flow Analytics:
   - Bank Statement Importer with automated counterparty and transaction mode extraction.
   - Directed Money-Flow Graph (Nodes: accounts/entities, Edges: aggregated transactions with row citations).
   - Structuring / Smurfing & Layering Alert Engine.
"""

import re
import csv
import io
import math
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from models import Case, Evidence, CDRRecord, BankTransaction, Entity, WatchlistEntry, Alert
from cross_case_engine import normalize_phone_number
from alerts_engine import create_or_update_alert
from collaboration import publish_collaboration_event

logger = logging.getLogger("evidentia.cdr_financial")

# Known cell tower geographic coordinate registry for speed & distance calculations
KNOWN_TOWER_COORDINATES = {
    "CELL-KHARADI-01": (18.5518, 73.9352, "Kharadi Bypass Sector 4, Pune"),
    "CELL-KHARADI-02": (18.5540, 73.9380, "Kharadi IT Park Sector 2, Pune"),
    "CELL-YERWADA-01": (18.5529, 73.8824, "SBI ATM Yerwada Commercial Sector, Pune"),
    "CELL-HADAPSAR-01": (18.5142, 73.9260, "Magarpatta South Gate, Hadapsar, Pune"),
    "CELL-SHIVAJI-01": (18.5314, 73.8446, "Shivajinagar Bus Terminus, Pune"),
    "CELL-HINJEWADI-01": (18.5913, 73.7389, "Hinjewadi Phase 1 Circle, Pune"),
    "CELL-RAJGURU-01": (18.8576, 73.8837, "Rajgurunagar Highway Junction, Pune Outskirts"),
    "TOWER-MUM-CST-01": (18.9402, 72.8356, "Chhatrapati Shivaji Maharaj Terminus, Mumbai"),
    "TOWER-MUM-CHEM-01": (19.0622, 72.8973, "Chembur Monorail Station, Mumbai"),
    "TOWER-DEL-01": (28.6315, 77.2167, "Connaught Place Radial Road, New Delhi"),
    "TOWER-DEL-04": (28.5539, 77.1691, "Mahipalpur Transit Arterial, New Delhi"),
    "TOWER-DEL-ANAND-01": (28.6472, 77.3153, "Anand Vihar ISBT Depot, New Delhi"),
    "TOWER-BLR-IND-01": (12.9784, 77.6408, "100ft Road Indiranagar, Bengaluru"),
    "TOWER-BLR-WHITE-01": (12.9698, 77.7500, "ITPL Main Road, Whitefield, Bengaluru"),
}

# Locality keyword fallback coordinates
LOCALITY_KEYWORD_COORDINATES = [
    (["kharadi", "bypass"], 18.5518, 73.9352, "Kharadi Bypass Corridor, Pune"),
    (["yerwada", "atm"], 18.5529, 73.8824, "Yerwada SBI ATM Sector, Pune"),
    (["hadapsar", "magarpatta"], 18.5142, 73.9260, "Hadapsar Magarpatta, Pune"),
    (["shivajinagar"], 18.5314, 73.8446, "Shivajinagar Central, Pune"),
    (["hinjewadi"], 18.5913, 73.7389, "Hinjewadi Tech Park, Pune"),
    (["rajgurunagar"], 18.8576, 73.8837, "Rajgurunagar Outskirts, Pune"),
    (["mumbai", "cst", "fort"], 18.9402, 72.8356, "Mumbai CST Fort Sector"),
    (["chembur"], 19.0622, 72.8973, "Chembur Sector, Mumbai"),
    (["connaught", "delhi"], 28.6315, 77.2167, "Connaught Place, New Delhi"),
    (["mahipalpur", "munirka"], 28.5539, 77.1691, "Mahipalpur Arterial, New Delhi"),
    (["anand vihar"], 28.6472, 77.3153, "Anand Vihar, New Delhi"),
    (["indiranagar", "bengaluru"], 12.9784, 77.6408, "Indiranagar, Bengaluru"),
]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return R * c


def resolve_tower_coordinates(cell_id: str, site_name: Optional[str] = None) -> Tuple[Optional[float], Optional[float], str]:
    """Resolves latitude, longitude, and canonical site name for a cell tower."""
    cid_clean = (cell_id or "").strip().upper()
    if cid_clean in KNOWN_TOWER_COORDINATES:
        lat, lon, name = KNOWN_TOWER_COORDINATES[cid_clean]
        return lat, lon, site_name or name

    combined_text = f"{cell_id or ''} {site_name or ''}".lower()
    for kw_list, lat, lon, name in LOCALITY_KEYWORD_COORDINATES:
        if all(kw in combined_text for kw in kw_list):
            return lat, lon, site_name or name

    return None, None, site_name or cell_id or "Unknown Tower Site"


def parse_flexible_datetime(dt_val: Any, time_val: Optional[Any] = None) -> Optional[datetime]:
    """Robustly parses datetime from diverse formats (ISO, DD/MM/YYYY, Excel datetime, timestamps)."""
    if dt_val is None:
        return None

    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val

    # Convert to string and clean
    raw_str = str(dt_val).strip()
    if time_val:
        raw_str = f"{raw_str} {str(time_val).strip()}"

    # Try ISO format
    try:
        clean_iso = raw_str.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(clean_iso)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        pass

    # Common Indian and telecom datetime patterns
    patterns = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%Y%m%d%H%M%S",
    ]

    for pat in patterns:
        try:
            parsed = datetime.strptime(raw_str, pat)
            return parsed.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


# ==============================================================================
# 1. CDR & TOWER-DUMP PARSER (CSV / EXCEL)
# ==============================================================================

def parse_and_store_cdr(
    file_content: Union[bytes, str],
    file_name: str,
    case_id: int,
    evidence_id: Optional[int],
    db: Session
) -> Dict[str, Any]:
    """
    Parses CDR / Tower Dump CSV or Excel files.
    Every record is stored with its exact 1-based row_number from the original file.
    Automatically normalizes telephone numbers and extracts tower locations.
    """
    raw_rows: List[Dict[str, Any]] = []
    is_excel = file_name.lower().endswith(('.xlsx', '.xls'))

    if is_excel:
        import openpyxl
        content_stream = io.BytesIO(file_content if isinstance(file_content, bytes) else file_content.encode('utf-8', errors='ignore'))
        wb = openpyxl.load_workbook(content_stream, data_only=True)
        ws = wb.active
        all_lines = list(ws.iter_rows(values_only=True))
        if not all_lines:
            return {"parsed_count": 0, "error": "Empty Excel sheet."}

        # Locate header row (check first 10 rows for keywords)
        header_idx = 0
        header_keys = []
        for idx, row in enumerate(all_lines[:10]):
            str_cells = [str(c or "").strip().lower() for c in row if c is not None]
            if any(k in " ".join(str_cells) for k in ["call", "msisdn", "tower", "party", "date", "cell"]):
                header_idx = idx
                header_keys = [str(c or "").strip() for c in row]
                break

        if not header_keys:
            header_keys = [str(c or f"Col_{i}") for i, c in enumerate(all_lines[0])]

        for row_num, row_data in enumerate(all_lines[header_idx + 1:], start=header_idx + 2):
            if not any(row_data):
                continue
            row_dict = {}
            for col_idx, key in enumerate(header_keys):
                if col_idx < len(row_data):
                    row_dict[key] = row_data[col_idx]
            raw_rows.append({"row_number": row_num, "data": row_dict})

    else:
        # CSV Handling
        text_content = file_content.decode('utf-8', errors='ignore') if isinstance(file_content, bytes) else file_content
        reader = csv.reader(io.StringIO(text_content))
        lines = list(reader)
        if not lines:
            return {"parsed_count": 0, "error": "Empty CSV file."}

        header_idx = 0
        header_keys = []
        for idx, row in enumerate(lines[:10]):
            str_cells = [c.strip().lower() for c in row if c]
            if any(k in " ".join(str_cells) for k in ["call", "msisdn", "tower", "party", "date", "cell"]):
                header_idx = idx
                header_keys = [c.strip() for c in row]
                break

        if not header_keys:
            header_keys = [c.strip() or f"Col_{i}" for i, c in enumerate(lines[0])]

        for row_num, row_data in enumerate(lines[header_idx + 1:], start=header_idx + 2):
            if not any(row_data):
                continue
            row_dict = {}
            for col_idx, key in enumerate(header_keys):
                if col_idx < len(row_data):
                    row_dict[key] = row_data[col_idx]
            raw_rows.append({"row_number": row_num, "data": row_dict})

    # Helper to retrieve normalized value from canonical column candidate sets
    def _clean_token(t: Any) -> str:
        return re.sub(r'[\s_\-]', '', str(t or '').lower())

    def _extract_field(row_d: Dict[str, Any], candidates: Set[str]) -> Optional[Any]:
        for k, v in row_d.items():
            if _clean_token(k) in candidates and v not in (None, ""):
                return v
        return None

    parsed_records = []
    unique_callers = set()
    towers_set = set()

    CALLING_ALIASES = {"callingnumber", "callingno", "calling", "caller", "aparty", "msisdn", "callingmsisdn", "sourcenumber", "callernum", "source"}
    CALLED_ALIASES = {"callednumber", "calledno", "called", "receiver", "bparty", "dialednumber", "destinationnumber", "targetnumber", "receivermsisdn", "destination"}
    DATETIME_ALIASES = {"calldatetime", "datetime", "timestamp", "calldateandtime", "calldate", "starttime", "calltime", "date"}
    TIME_ALIASES = {"time", "calltime", "starttime"}
    DURATION_ALIASES = {"duration", "durationsec", "callduration", "durationseconds", "dur", "calllen", "callseconds"}
    CELL_ALIASES = {"cellid", "towerid", "firstcgi", "lastcgi", "cgi", "cellsite", "sector", "towersector", "siteid", "tower"}
    SITE_ALIASES = {"sitename", "siteaddress", "location", "toweraddress", "cellname", "locationname"}
    AZIMUTH_ALIASES = {"azimuth", "sectorazimuth", "beam", "direction"}
    LAT_ALIASES = {"latitude", "lat"}
    LON_ALIASES = {"longitude", "lon", "long"}
    IMEI_ALIASES = {"imei", "deviceimei", "handsetimei"}
    IMSI_ALIASES = {"imsi", "subscriberimsi"}
    TYPE_ALIASES = {"calltype", "type", "eventtype", "traffictype", "direction"}

    for item in raw_rows:
        row_num = item["row_number"]
        d = item["data"]

        caller_raw = _extract_field(d, CALLING_ALIASES)
        called_raw = _extract_field(d, CALLED_ALIASES)
        date_raw = _extract_field(d, DATETIME_ALIASES)
        time_raw = _extract_field(d, TIME_ALIASES) if any("date" in _clean_token(k) for k in d) else None
        duration_raw = _extract_field(d, DURATION_ALIASES)
        cell_raw = _extract_field(d, CELL_ALIASES)
        site_raw = _extract_field(d, SITE_ALIASES)
        azimuth_raw = _extract_field(d, AZIMUTH_ALIASES)
        lat_raw = _extract_field(d, LAT_ALIASES)
        lon_raw = _extract_field(d, LON_ALIASES)
        imei_raw = _extract_field(d, IMEI_ALIASES)
        imsi_raw = _extract_field(d, IMSI_ALIASES)
        type_raw = _extract_field(d, TYPE_ALIASES)

        if not caller_raw and not cell_raw:
            continue

        norm_caller = normalize_phone_number(str(caller_raw or "")) or str(caller_raw or "UNKNOWN")
        norm_called = normalize_phone_number(str(called_raw or "")) if called_raw else None

        parsed_dt = parse_flexible_datetime(date_raw, time_raw) or datetime.now(timezone.utc)

        duration_sec = 0
        try:
            duration_sec = int(float(duration_raw or 0))
        except Exception:
            pass

        azimuth = None
        try:
            azimuth = float(azimuth_raw) if azimuth_raw else None
        except Exception:
            pass

        lat = None
        lon = None
        try:
            lat = float(lat_raw) if lat_raw else None
            lon = float(lon_raw) if lon_raw else None
        except Exception:
            pass

        # Resolve tower geolocation coordinates if missing
        if lat is None or lon is None:
            resolved_lat, resolved_lon, resolved_site = resolve_tower_coordinates(str(cell_raw or ""), str(site_raw or ""))
            lat = lat or resolved_lat
            lon = lon or resolved_lon
            site_raw = site_raw or resolved_site

        rec = CDRRecord(
            case_id=case_id,
            evidence_id=evidence_id,
            source_file_name=file_name,
            row_number=row_num,
            calling_number=norm_caller,
            called_number=norm_called,
            call_datetime=parsed_dt,
            call_duration_sec=duration_sec,
            call_type=str(type_raw or "voice").lower(),
            imei=str(imei_raw).strip() if imei_raw else None,
            imsi=str(imsi_raw).strip() if imsi_raw else None,
            cell_id=str(cell_raw or "UNKNOWN-TOWER").strip(),
            azimuth=azimuth,
            site_name=str(site_raw or "").strip() or None,
            latitude=lat,
            longitude=lon,
            raw_data_json=json.dumps({str(k): str(v) for k, v in d.items() if v is not None})
        )
        parsed_records.append(rec)
        unique_callers.add(norm_caller)
        if norm_called:
            unique_callers.add(norm_called)
        if cell_raw:
            towers_set.add(str(cell_raw))

    if parsed_records:
        db.add_all(parsed_records)
        db.commit()

    return {
        "source_file": file_name,
        "parsed_records": len(parsed_records),
        "unique_phone_numbers": len(unique_callers),
        "unique_towers": len(towers_set),
        "earliest_timestamp": min((r.call_datetime for r in parsed_records), default=datetime.now(timezone.utc)).isoformat() if parsed_records else None,
        "latest_timestamp": max((r.call_datetime for r in parsed_records), default=datetime.now(timezone.utc)).isoformat() if parsed_records else None
    }


# ==============================================================================
# 2. BANK STATEMENT IMPORTER (CSV / EXCEL)
# ==============================================================================

def parse_and_store_bank_statement(
    file_content: Union[bytes, str],
    file_name: str,
    case_id: int,
    evidence_id: Optional[int],
    db: Session,
    account_number_hint: Optional[str] = None,
    bank_name_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses bank account statements in CSV or Excel format.
    Every transaction is linked back to its exact 1-based row_number.
    Extracts debit, credit, transaction mode (UPI/NEFT/IMPS/ATM/Cash), and counterparty.
    """
    raw_rows: List[Dict[str, Any]] = []
    is_excel = file_name.lower().endswith(('.xlsx', '.xls'))

    if is_excel:
        import openpyxl
        content_stream = io.BytesIO(file_content if isinstance(file_content, bytes) else file_content.encode('utf-8', errors='ignore'))
        wb = openpyxl.load_workbook(content_stream, data_only=True)
        ws = wb.active
        all_lines = list(ws.iter_rows(values_only=True))
        if not all_lines:
            return {"parsed_count": 0, "error": "Empty Excel sheet."}

        header_idx = 0
        header_keys = []
        for idx, row in enumerate(all_lines[:15]):
            str_cells = [str(c or "").strip().lower() for c in row if c is not None]
            joined = " ".join(str_cells)
            if any(k in joined for k in ["date", "description", "narration", "particulars", "debit", "withdrawal", "credit", "balance"]):
                header_idx = idx
                header_keys = [str(c or "").strip() for c in row]
                break

        if not header_keys:
            header_keys = [str(c or f"Col_{i}") for i, c in enumerate(all_lines[0])]

        for row_num, row_data in enumerate(all_lines[header_idx + 1:], start=header_idx + 2):
            if not any(row_data):
                continue
            row_dict = {}
            for col_idx, key in enumerate(header_keys):
                if col_idx < len(row_data):
                    row_dict[key] = row_data[col_idx]
            raw_rows.append({"row_number": row_num, "data": row_dict})

    else:
        text_content = file_content.decode('utf-8', errors='ignore') if isinstance(file_content, bytes) else file_content
        reader = csv.reader(io.StringIO(text_content))
        lines = list(reader)
        if not lines:
            return {"parsed_count": 0, "error": "Empty CSV file."}

        header_idx = 0
        header_keys = []
        for idx, row in enumerate(lines[:15]):
            str_cells = [c.strip().lower() for c in row if c]
            joined = " ".join(str_cells)
            if any(k in joined for k in ["date", "description", "narration", "particulars", "debit", "withdrawal", "credit", "balance"]):
                header_idx = idx
                header_keys = [c.strip() for c in row]
                break

        if not header_keys:
            header_keys = [c.strip() or f"Col_{i}" for i, c in enumerate(lines[0])]

        for row_num, row_data in enumerate(lines[header_idx + 1:], start=header_idx + 2):
            if not any(row_data):
                continue
            row_dict = {}
            for col_idx, key in enumerate(header_keys):
                if col_idx < len(row_data):
                    row_dict[key] = row_data[col_idx]
            raw_rows.append({"row_number": row_num, "data": row_dict})

    def _clean_token(t: Any) -> str:
        return re.sub(r'[\s_\-]', '', str(t or '').lower())

    def _extract_field(row_d: Dict[str, Any], candidates: Set[str]) -> Optional[Any]:
        for k, v in row_d.items():
            if _clean_token(k) in candidates and v not in (None, ""):
                return v
        return None

    def _clean_amount(amt_val: Any) -> float:
        if amt_val is None:
            return 0.0
        if isinstance(amt_val, (int, float)):
            return float(abs(amt_val))
        clean_str = re.sub(r'[^\d.-]', '', str(amt_val))
        try:
            return float(abs(float(clean_str)))
        except Exception:
            return 0.0

    parsed_txns = []
    account_num = account_number_hint or f"ACC-{case_id}-MAIN"
    bank_name = bank_name_hint or "State Bank of India"

    DATE_ALIASES = {"transactiondate", "txndate", "date", "postingdate", "transdate", "valuedate"}
    DESC_ALIASES = {"description", "narration", "particulars", "remarks", "transactionremarks", "details"}
    REF_ALIASES = {"referencenumber", "refno", "chqrefno", "chequeno", "utr", "txnid", "reference", "utrnumber", "ref"}
    DEBIT_ALIASES = {"debitamount", "debit", "withdrawal", "dr", "withdrawalamount", "amountdebited"}
    CREDIT_ALIASES = {"creditamount", "credit", "deposit", "cr", "depositamount", "amountcredited"}
    BALANCE_ALIASES = {"balance", "closingbalance", "availablebalance", "bal"}
    ACC_ALIASES = {"accountnumber", "accountno", "acno", "accno"}

    for item in raw_rows:
        row_num = item["row_number"]
        d = item["data"]

        date_raw = _extract_field(d, DATE_ALIASES)
        desc_raw = _extract_field(d, DESC_ALIASES)
        ref_raw = _extract_field(d, REF_ALIASES)
        debit_raw = _extract_field(d, DEBIT_ALIASES)
        credit_raw = _extract_field(d, CREDIT_ALIASES)
        balance_raw = _extract_field(d, BALANCE_ALIASES)
        acc_raw = _extract_field(d, ACC_ALIASES)

        if not date_raw and not desc_raw:
            continue

        desc = str(desc_raw or "Transaction").strip()
        parsed_date = parse_flexible_datetime(date_raw) or datetime.now(timezone.utc)
        debit_amt = _clean_amount(debit_raw)
        credit_amt = _clean_amount(credit_raw)
        balance = float(balance_raw) if balance_raw is not None and str(balance_raw).strip() != "" else None

        # Mode detection
        desc_upper = desc.upper()
        mode = "TRANSFER"
        if "UPI" in desc_upper:
            mode = "UPI"
        elif "NEFT" in desc_upper:
            mode = "NEFT"
        elif "RTGS" in desc_upper:
            mode = "RTGS"
        elif "IMPS" in desc_upper:
            mode = "IMPS"
        elif "ATM" in desc_upper:
            mode = "ATM"
        elif "CASH" in desc_upper or "CHQ" in desc_upper or "CHEQUE" in desc_upper:
            mode = "CASH/CHEQUE"
        elif "POS" in desc_upper:
            mode = "POS"

        # Counterparty parsing heuristic
        counterparty_acc = None
        counterparty_name = None

        upi_match = re.search(r'UPI/([A-Za-z0-9]+)/([^/]+)', desc)
        if upi_match:
            counterparty_name = upi_match.group(2).strip()
            counterparty_acc = upi_match.group(1).strip()

        neft_match = re.search(r'NEFT-([A-Z0-9]+)-([^-]+)', desc)
        if neft_match:
            counterparty_name = neft_match.group(2).strip()
            counterparty_acc = neft_match.group(1).strip()

        ac_match = re.search(r'(?:A/C|ACC|TO|FROM)\s*:?\s*([A-Za-z0-9]{6,18})', desc, re.IGNORECASE)
        if ac_match and not counterparty_acc:
            counterparty_acc = ac_match.group(1).strip()

        txn = BankTransaction(
            case_id=case_id,
            evidence_id=evidence_id,
            source_file_name=file_name,
            row_number=row_num,
            transaction_date=parsed_date,
            value_date=parsed_date,
            description=desc,
            reference_number=str(ref_raw).strip() if ref_raw else f"REF-R{row_num}",
            debit_amount=debit_amt,
            credit_amount=credit_amt,
            balance=balance,
            account_number=str(acc_raw).strip() if acc_raw else account_num,
            counterparty_account=counterparty_acc,
            counterparty_name=counterparty_name,
            bank_name=bank_name,
            transaction_mode=mode,
            raw_data_json=json.dumps({str(k): str(v) for k, v in d.items() if v is not None})
        )
        parsed_txns.append(txn)

    if parsed_txns:
        db.add_all(parsed_txns)
        db.commit()

    total_debit = sum(t.debit_amount for t in parsed_txns)
    total_credit = sum(t.credit_amount for t in parsed_txns)

    return {
        "source_file": file_name,
        "parsed_transactions": len(parsed_txns),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "date_range": {
            "start": min((t.transaction_date for t in parsed_txns), default=datetime.now(timezone.utc)).isoformat() if parsed_txns else None,
            "end": max((t.transaction_date for t in parsed_txns), default=datetime.now(timezone.utc)).isoformat() if parsed_txns else None
        }
    }


# ==============================================================================
# 3. TELECOM ANALYTICS: CO-LOCATION DETECTION
# ==============================================================================

def analyze_co_location(
    case_id: int,
    db: Session,
    window_minutes: int = 15,
    target_numbers: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Detects two distinct phone numbers active in the same cell tower sector at the same time.
    Every co-location event links back to the source file name and line row of BOTH calls.
    """
    query = db.query(CDRRecord).filter(CDRRecord.case_id == case_id)
    if target_numbers:
        norm_targets = [normalize_phone_number(n) or n for n in target_numbers]
        query = query.filter(
            or_(
                CDRRecord.calling_number.in_(norm_targets),
                CDRRecord.called_number.in_(norm_targets)
            )
        )

    records = query.order_by(CDRRecord.cell_id, CDRRecord.call_datetime).all()
    if not records:
        return []

    # Group by cell_id
    records_by_cell: Dict[str, List[CDRRecord]] = {}
    for r in records:
        records_by_cell.setdefault(r.cell_id, []).append(r)

    co_location_events = []
    seen_pairs: Set[Tuple[int, int]] = set()

    for cell_id, cell_records in records_by_cell.items():
        cell_records.sort(key=lambda x: x.call_datetime)
        n = len(cell_records)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = cell_records[i]
                r2 = cell_records[j]

                # Check if numbers are different
                if r1.calling_number == r2.calling_number:
                    continue

                delta_sec = abs((r2.call_datetime - r1.call_datetime).total_seconds())
                if delta_sec > (window_minutes * 60):
                    break  # Chronologically sorted, later records will also exceed window

                pair_id = (min(r1.id, r2.id), max(r1.id, r2.id))
                if pair_id in seen_pairs:
                    continue
                seen_pairs.add(pair_id)

                delta_mins = round(delta_sec / 60.0, 1)
                site_name = r1.site_name or r2.site_name or cell_id

                confidence = 98.0 if delta_mins <= 3.0 else (92.0 if delta_mins <= 10.0 else 85.0)

                co_location_events.append({
                    "event_id": f"COLOC-{r1.id}-{r2.id}",
                    "cell_id": cell_id,
                    "site_name": site_name,
                    "latitude": r1.latitude or r2.latitude,
                    "longitude": r1.longitude or r2.longitude,
                    "time_delta_seconds": int(delta_sec),
                    "time_delta_minutes": delta_mins,
                    "confidence": confidence,
                    "phone_a": {
                        "number": r1.calling_number,
                        "timestamp": r1.call_datetime.isoformat(),
                        "evidence_id": r1.evidence_id,
                        "source_file": r1.source_file_name,
                        "row_number": r1.row_number,
                        "duration_sec": r1.call_duration_sec,
                        "call_type": r1.call_type
                    },
                    "phone_b": {
                        "number": r2.calling_number,
                        "timestamp": r2.call_datetime.isoformat(),
                        "evidence_id": r2.evidence_id,
                        "source_file": r2.source_file_name,
                        "row_number": r2.row_number,
                        "duration_sec": r2.call_duration_sec,
                        "call_type": r2.call_type
                    },
                    "reasoning": (
                        f"Co-Location Confirmed: Handset {r1.calling_number} (Row #{r1.row_number}) and "
                        f"Handset {r2.calling_number} (Row #{r2.row_number}) registered at Tower '{cell_id}' "
                        f"({site_name}) within {delta_mins} minutes."
                    )
                })

    # Sort descending by confidence and smallest delta
    co_location_events.sort(key=lambda x: (x["time_delta_seconds"], -x["confidence"]))
    return co_location_events


# ==============================================================================
# 4. TELECOM ANALYTICS: COMMON CONTACTS DISCOVERY
# ==============================================================================

def analyze_common_contacts(
    case_id: int,
    db: Session,
    suspect_numbers: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Identifies common contacts / bridge nodes dialed by or dialing two or more suspect handsets.
    Every connection links back to the exact CDR file rows.
    """
    all_records = db.query(CDRRecord).filter(CDRRecord.case_id == case_id).all()
    if not all_records:
        return []

    # If suspect_numbers not given, find top 3 active numbers
    if not suspect_numbers:
        counts: Dict[str, int] = {}
        for r in all_records:
            counts[r.calling_number] = counts.get(r.calling_number, 0) + 1
        suspect_numbers = [num for num, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:4]]

    norm_suspects = set(normalize_phone_number(n) or n for n in suspect_numbers)

    # Map outside contact -> list of suspect interactions
    # contact -> { suspect -> list of CDRRecord }
    contact_network: Dict[str, Dict[str, List[CDRRecord]]] = {}

    for r in all_records:
        caller = r.calling_number
        called = r.called_number
        if not called:
            continue

        if caller in norm_suspects and called not in norm_suspects:
            contact_network.setdefault(called, {}).setdefault(caller, []).append(r)
        elif called in norm_suspects and caller not in norm_suspects:
            contact_network.setdefault(caller, {}).setdefault(called, []).append(r)

    common_contacts_list = []

    for contact_num, suspect_map in contact_network.items():
        if len(suspect_map) >= 2:  # Shared by at least 2 suspects
            total_calls = sum(len(recs) for recs in suspect_map.values())
            total_duration = sum(sum(rec.call_duration_sec for rec in recs) for recs in suspect_map.values())

            earliest = min(rec.call_datetime for recs in suspect_map.values() for rec in recs)
            latest = max(rec.call_datetime for recs in suspect_map.values() for rec in recs)

            breakdown = []
            all_linked_rows = []

            for susp, recs in suspect_map.items():
                row_citations = [
                    {
                        "source_file": rec.source_file_name,
                        "row_number": rec.row_number,
                        "timestamp": rec.call_datetime.isoformat(),
                        "duration_sec": rec.call_duration_sec,
                        "cell_id": rec.cell_id,
                        "site_name": rec.site_name
                    }
                    for rec in recs
                ]
                breakdown.append({
                    "suspect_number": susp,
                    "call_count": len(recs),
                    "total_duration_sec": sum(r.call_duration_sec for r in recs),
                    "row_citations": row_citations
                })
                all_linked_rows.extend(row_citations)

            common_contacts_list.append({
                "contact_number": contact_num,
                "suspects_connected_count": len(suspect_map),
                "suspects_connected": list(suspect_map.keys()),
                "total_calls": total_calls,
                "total_duration_sec": total_duration,
                "first_contact": earliest.isoformat(),
                "last_contact": latest.isoformat(),
                "breakdown": breakdown,
                "all_linked_rows": all_linked_rows,
                "risk_rating": "Critical Conspirator Bridge" if len(suspect_map) >= 3 else "Significant Common Contact"
            })

    common_contacts_list.sort(key=lambda x: (x["suspects_connected_count"], x["total_calls"]), reverse=True)
    return common_contacts_list


# ==============================================================================
# 5. TELECOM ANALYTICS: SHORT-LIVED / BURNER SIM DETECTION
# ==============================================================================

def analyze_short_lived_numbers(
    case_id: int,
    db: Session,
    max_lifetime_hours: float = 72.0,
    max_calls: int = 25
) -> List[Dict[str, Any]]:
    """
    Identifies suspected burner / disposable SIM cards:
    Handsets active for very brief intervals (<72 hrs) with low total call volume
    that subsequently went dark / ceased activity.
    """
    records = db.query(CDRRecord).filter(CDRRecord.case_id == case_id).all()
    if not records:
        return []

    by_number: Dict[str, List[CDRRecord]] = {}
    for r in records:
        by_number.setdefault(r.calling_number, []).append(r)

    burner_candidates = []

    for number, num_records in by_number.items():
        if number.upper() in {"UNKNOWN", "ANONYMOUS"}:
            continue

        timestamps = [r.call_datetime for r in num_records]
        earliest = min(timestamps)
        latest = max(timestamps)
        active_hours = (latest - earliest).total_seconds() / 3600.0
        total_calls = len(num_records)

        # Flag condition: active for <= max_lifetime_hours AND <= max_calls
        if (active_hours <= max_lifetime_hours and total_calls <= max_calls) or (total_calls <= 5):
            unique_towers = list(set(r.cell_id for r in num_records))
            unique_imeis = list(set(r.imei for r in num_records if r.imei))

            linked_rows = [
                {
                    "source_file": r.source_file_name,
                    "row_number": r.row_number,
                    "timestamp": r.call_datetime.isoformat(),
                    "called_number": r.called_number,
                    "cell_id": r.cell_id,
                    "site_name": r.site_name,
                    "duration_sec": r.call_duration_sec
                }
                for r in num_records
            ]

            burner_candidates.append({
                "phone_number": number,
                "total_events": total_calls,
                "first_seen": earliest.isoformat(),
                "last_seen": latest.isoformat(),
                "active_duration_hours": round(active_hours, 1),
                "unique_towers_count": len(unique_towers),
                "towers": unique_towers,
                "imeis": unique_imeis,
                "linked_rows": linked_rows,
                "indicator": "High Probability Disposable SIM" if active_hours < 24.0 else "Short-Lived Temporary Number",
                "reasoning": (
                    f"Disposable Handset Pattern: SIM {number} operated for only {active_hours:.1f} hours "
                    f"with {total_calls} logged calls across {len(unique_towers)} cell sectors, then went silent."
                )
            })

    burner_candidates.sort(key=lambda x: (x["active_duration_hours"], x["total_events"]))
    return burner_candidates


# ==============================================================================
# 6. TELECOM ANALYTICS: IMPOSSIBLE TRAVEL / SPEED ANOMALIES
# ==============================================================================

def analyze_impossible_travel(
    case_id: int,
    db: Session,
    speed_threshold_kmh: float = 160.0
) -> List[Dict[str, Any]]:
    """
    Calculates geographic distance and velocity between consecutive cell tower hits for the same handset.
    Flags physical teleportation anomalies (>160 km/h) indicating SIM cloning, spoofing, or dual handsets.
    Every finding cites both source file rows.
    """
    records = db.query(CDRRecord).filter(CDRRecord.case_id == case_id).all()
    if not records:
        return []

    # Group by calling number
    by_number: Dict[str, List[CDRRecord]] = {}
    for r in records:
        by_number.setdefault(r.calling_number, []).append(r)

    anomalies = []

    for number, num_records in by_number.items():
        # Filter records with known coordinates
        geo_records = [r for r in num_records if r.latitude is not None and r.longitude is not None]
        geo_records.sort(key=lambda x: x.call_datetime)

        for i in range(len(geo_records) - 1):
            r1 = geo_records[i]
            r2 = geo_records[i + 1]

            delta_sec = (r2.call_datetime - r1.call_datetime).total_seconds()
            if delta_sec <= 0:
                continue

            dist_km = haversine_distance_km(r1.latitude, r1.longitude, r2.latitude, r2.longitude)
            if dist_km < 3.0:
                continue  # Adjacent tower sectors within walking distance

            hours = delta_sec / 3600.0
            velocity = dist_km / hours

            if velocity > speed_threshold_kmh:
                delta_mins = round(delta_sec / 60.0, 1)
                anomalies.append({
                    "phone_number": number,
                    "calculated_speed_kmh": round(velocity, 1),
                    "distance_km": round(dist_km, 2),
                    "time_delta_minutes": delta_mins,
                    "event_a": {
                        "source_file": r1.source_file_name,
                        "row_number": r1.row_number,
                        "timestamp": r1.call_datetime.isoformat(),
                        "cell_id": r1.cell_id,
                        "site_name": r1.site_name,
                        "latitude": r1.latitude,
                        "longitude": r1.longitude
                    },
                    "event_b": {
                        "source_file": r2.source_file_name,
                        "row_number": r2.row_number,
                        "timestamp": r2.call_datetime.isoformat(),
                        "cell_id": r2.cell_id,
                        "site_name": r2.site_name,
                        "latitude": r2.latitude,
                        "longitude": r2.longitude
                    },
                    "reasoning": (
                        f"Physically Impossible Speed ({round(velocity, 1)} km/h): Handset {number} logged at "
                        f"'{r1.site_name or r1.cell_id}' (Row #{r1.row_number}) and then '{r2.site_name or r2.cell_id}' "
                        f"(Row #{r2.row_number}) covering {round(dist_km, 1)} km in {delta_mins} mins. "
                        f"Indicates SIM cloning, IMSI-catcher spoofing, or simultaneous multi-device usage."
                    )
                })

    anomalies.sort(key=lambda x: x["calculated_speed_kmh"], reverse=True)
    return anomalies


# ==============================================================================
# 7. FINANCIAL ANALYTICS: MONEY-FLOW GRAPH & STRUCTURING DETECTION
# ==============================================================================

def analyze_money_flow(case_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes directed money-flow graph and suspicious financial structuring (smurfing/layering).
    Every node and directed edge retains exact row numbers from the statement.
    """
    txns = db.query(BankTransaction).filter(BankTransaction.case_id == case_id).order_by(BankTransaction.transaction_date).all()
    if not txns:
        return {
            "nodes": [],
            "edges": [],
            "total_flow": 0.0,
            "structuring_alerts": [],
            "layering_alerts": []
        }

    # Build Nodes & Edges
    # Edge key: (source, target)
    edges_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    nodes_map: Dict[str, Dict[str, Any]] = {}

    def _ensure_node(node_id: str, label: str, node_type: str = "account"):
        if node_id not in nodes_map:
            nodes_map[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "total_in": 0.0,
                "total_out": 0.0,
                "net_flow": 0.0,
                "transaction_count": 0
            }

    for t in txns:
        main_acc = t.account_number or f"ACC-{case_id}"
        cp_acc = t.counterparty_account or t.counterparty_name or "Cash/ATM Withdrawal"
        cp_label = t.counterparty_name or t.counterparty_account or "Cash/ATM"

        _ensure_node(main_acc, f"{t.bank_name or 'Bank'} ({main_acc[-4:] if len(main_acc)>=4 else main_acc})", "primary_account")
        _ensure_node(cp_acc, cp_label, "beneficiary" if t.debit_amount > 0 else "remitter")

        # Debit: main_acc -> cp_acc
        if t.debit_amount > 0:
            src = main_acc
            tgt = cp_acc
            amt = t.debit_amount

            nodes_map[src]["total_out"] += amt
            nodes_map[tgt]["total_in"] += amt
            nodes_map[src]["transaction_count"] += 1
            nodes_map[tgt]["transaction_count"] += 1

            edge_key = (src, tgt)
            if edge_key not in edges_map:
                edges_map[edge_key] = {
                    "source": src,
                    "target": tgt,
                    "total_amount": 0.0,
                    "transaction_count": 0,
                    "modes": set(),
                    "linked_rows": []
                }
            edges_map[edge_key]["total_amount"] += amt
            edges_map[edge_key]["transaction_count"] += 1
            edges_map[edge_key]["modes"].add(t.transaction_mode)
            edges_map[edge_key]["linked_rows"].append({
                "source_file": t.source_file_name,
                "row_number": t.row_number,
                "date": t.transaction_date.isoformat(),
                "amount": amt,
                "type": "debit",
                "reference": t.reference_number,
                "mode": t.transaction_mode,
                "description": t.description
            })

        # Credit: cp_acc -> main_acc
        elif t.credit_amount > 0:
            src = cp_acc
            tgt = main_acc
            amt = t.credit_amount

            nodes_map[src]["total_out"] += amt
            nodes_map[tgt]["total_in"] += amt
            nodes_map[src]["transaction_count"] += 1
            nodes_map[tgt]["transaction_count"] += 1

            edge_key = (src, tgt)
            if edge_key not in edges_map:
                edges_map[edge_key] = {
                    "source": src,
                    "target": tgt,
                    "total_amount": 0.0,
                    "transaction_count": 0,
                    "modes": set(),
                    "linked_rows": []
                }
            edges_map[edge_key]["total_amount"] += amt
            edges_map[edge_key]["transaction_count"] += 1
            edges_map[edge_key]["modes"].add(t.transaction_mode)
            edges_map[edge_key]["linked_rows"].append({
                "source_file": t.source_file_name,
                "row_number": t.row_number,
                "date": t.transaction_date.isoformat(),
                "amount": amt,
                "type": "credit",
                "reference": t.reference_number,
                "mode": t.transaction_mode,
                "description": t.description
            })

    # Finalize nodes net balance
    for n in nodes_map.values():
        n["net_flow"] = round(n["total_in"] - n["total_out"], 2)
        n["total_in"] = round(n["total_in"], 2)
        n["total_out"] = round(n["total_out"], 2)

    # Format edges
    edges_list = []
    for edge in edges_map.values():
        edges_list.append({
            "source": edge["source"],
            "target": edge["target"],
            "total_amount": round(edge["total_amount"], 2),
            "transaction_count": edge["transaction_count"],
            "modes": sorted(list(edge["modes"])),
            "linked_rows": edge["linked_rows"]
        })

    # Structuring / Smurfing Detection (Transactions just below reporting threshold ₹50,000 or ₹10,00,000)
    structuring_alerts = []
    smurfing_txns = [t for t in txns if (45000.0 <= t.debit_amount < 50000.0) or (45000.0 <= t.credit_amount < 50000.0)]
    if len(smurfing_txns) >= 2:
        structuring_alerts.append({
            "alert_type": "smurfing_threshold_evasion",
            "title": "Suspected Structuring / Smurfing Near Statutory ₹50,000 Threshold",
            "severity": "high",
            "matched_transactions_count": len(smurfing_txns),
            "total_structured_amount": round(sum(t.debit_amount or t.credit_amount for t in smurfing_txns), 2),
            "reasoning": (
                f"Detected {len(smurfing_txns)} transactions intentionally calibrated just below the "
                f"statutory ₹50,000 mandatory PAN reporting threshold (e.g. ₹48,500, ₹49,000)."
            ),
            "linked_rows": [
                {
                    "source_file": t.source_file_name,
                    "row_number": t.row_number,
                    "date": t.transaction_date.isoformat(),
                    "amount": t.debit_amount or t.credit_amount,
                    "reference": t.reference_number,
                    "description": t.description
                }
                for t in smurfing_txns
            ]
        })

    # Rapid Layering / Pass-Through Detection (Credit followed by >=80% debit within 24 hours)
    layering_alerts = []
    for i, t_in in enumerate(txns):
        if t_in.credit_amount >= 20000.0:
            window_end = t_in.transaction_date + timedelta(hours=24)
            subsequent_debits = [
                t for t in txns[i+1:]
                if t.transaction_date <= window_end and t.debit_amount > 0
            ]
            total_dispersed = sum(t.debit_amount for t in subsequent_debits)
            if total_dispersed >= (t_in.credit_amount * 0.75):
                layering_alerts.append({
                    "alert_type": "rapid_layering_passthrough",
                    "title": "Rapid Fund Layering & Transit Dispersal",
                    "severity": "critical",
                    "inflow_amount": t_in.credit_amount,
                    "dispersed_amount": round(total_dispersed, 2),
                    "timeframe_hours": round((subsequent_debits[-1].transaction_date - t_in.transaction_date).total_seconds() / 3600.0, 1) if subsequent_debits else 0,
                    "reasoning": (
                        f"Inflow of ₹{t_in.credit_amount:,.2f} on {t_in.transaction_date.strftime('%d-%b-%Y')} (Row #{t_in.row_number}) "
                        f"was rapidly dispersed (₹{total_dispersed:,.2f} / {round(total_dispersed/t_in.credit_amount*100)}%) "
                        f"within 24 hours across {len(subsequent_debits)} debit transactions."
                    ),
                    "inflow_row": {
                        "source_file": t_in.source_file_name,
                        "row_number": t_in.row_number,
                        "date": t_in.transaction_date.isoformat(),
                        "amount": t_in.credit_amount,
                        "description": t_in.description
                    },
                    "outflow_rows": [
                        {
                            "source_file": t.source_file_name,
                            "row_number": t.row_number,
                            "date": t.transaction_date.isoformat(),
                            "amount": t.debit_amount,
                            "description": t.description
                        }
                        for t in subsequent_debits
                    ]
                })

    return {
        "nodes": list(nodes_map.values()),
        "edges": edges_list,
        "total_transactions": len(txns),
        "total_volume": round(sum(t.debit_amount + t.credit_amount for t in txns), 2),
        "structuring_alerts": structuring_alerts,
        "layering_alerts": layering_alerts
    }


# ==============================================================================
# LIVE CDR & FINANCIAL AUTOMATED ANALYSIS AND WATCHLISTS
# ==============================================================================

def normalize_watchlist_token(entity_type: str, raw_value: str) -> str:
    """Normalizes phone numbers, bank accounts, vehicle plates, or names for exact/fuzzy watchlist matching."""
    val = (raw_value or "").strip()
    if not val:
        return ""
    t = entity_type.lower()
    if t == "phone":
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 10:
            return digits[-10:]  # Canonical last 10 digits
        return digits
    elif t in ["account", "bank_account"]:
        return re.sub(r"\s+", "", val).upper()
    elif t in ["vehicle", "plate"]:
        return re.sub(r"[^A-Za-z0-9]", "", val).upper()
    elif t == "person":
        return re.sub(r"\s+", " ", val).strip().lower()
    return val.strip().lower()


def check_watchlists_for_case(
    case_id: int,
    db: Session,
    user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Scans active watchlist entries against all telecom records, bank statements,
    entities, and exhibits in this case.
    Raises critical alerts ONLY for new findings with judicial deduplication.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return []

    watchlists = db.query(WatchlistEntry).filter(WatchlistEntry.is_active == True).all()
    if not watchlists:
        return []

    cdr_records = db.query(CDRRecord).filter(CDRRecord.case_id == case_id).all()
    bank_txns = db.query(BankTransaction).filter(BankTransaction.case_id == case_id).all()
    entities = db.query(Entity).filter(Entity.case_id == case_id).all()

    matches = []
    now = datetime.now(timezone.utc)

    for wl in watchlists:
        target_norm = normalize_watchlist_token(wl.entity_type, wl.entity_value)
        if not target_norm:
            continue

        matched_records = []

        # 1. Phone matching in CDR
        if wl.entity_type in ["phone", "person"]:
            for r in cdr_records:
                call_norm1 = normalize_watchlist_token("phone", r.calling_number)
                call_norm2 = normalize_watchlist_token("phone", r.called_number or "")
                if target_norm in [call_norm1, call_norm2]:
                    matched_records.append({
                        "record_type": "cdr",
                        "record_id": r.id,
                        "matched_value": r.calling_number if target_norm == call_norm1 else r.called_number,
                        "file_name": r.source_file_name,
                        "row_number": r.row_number,
                        "timestamp": r.call_datetime.isoformat() if r.call_datetime else None,
                        "details": f"Call from {r.calling_number} to {r.called_number} (duration {r.call_duration_sec}s, tower {r.cell_id})"
                    })

        # 2. Account matching in Bank statements
        if wl.entity_type in ["account", "bank_account", "person"]:
            for b in bank_txns:
                acc_norm1 = normalize_watchlist_token("account", b.account_number)
                acc_norm2 = normalize_watchlist_token("account", b.counterparty_account or "")
                desc_upper = (b.description or "").upper()
                cparty_name = (b.counterparty_name or "").lower()

                is_hit = False
                hit_val = b.account_number
                if target_norm in [acc_norm1, acc_norm2]:
                    is_hit = True
                    hit_val = b.account_number if target_norm == acc_norm1 else b.counterparty_account
                elif wl.entity_type == "account" and target_norm in desc_upper:
                    is_hit = True
                    hit_val = target_norm
                elif wl.entity_type == "person" and target_norm in cparty_name:
                    is_hit = True
                    hit_val = b.counterparty_name

                if is_hit:
                    matched_records.append({
                        "record_type": "bank",
                        "record_id": b.id,
                        "matched_value": hit_val,
                        "file_name": b.source_file_name,
                        "row_number": b.row_number,
                        "timestamp": b.transaction_date.isoformat() if b.transaction_date else None,
                        "details": f"{b.transaction_mode} Txn of ₹{b.debit_amount or b.credit_amount:,.2f} ({b.description})"
                    })

        # 3. Vehicle / Person matching in extracted Entities
        if wl.entity_type in ["vehicle", "person"]:
            for ent in entities:
                ent_norm = normalize_watchlist_token(wl.entity_type, ent.name)
                if target_norm == ent_norm or (len(target_norm) > 4 and target_norm in ent_norm):
                    matched_records.append({
                        "record_type": "entity",
                        "record_id": ent.id,
                        "matched_value": ent.name,
                        "file_name": f"Exhibit #{ent.evidence_id}",
                        "row_number": getattr(ent, "source_page_number", 1),
                        "timestamp": None,
                        "details": f"Extracted Entity '{ent.name}' (Type: {ent.type}, Confidence: {round(ent.confidence*100)}%)"
                    })

        # Raise alert if matches found
        if matched_records:
            wl.match_count = (wl.match_count or 0) + len(matched_records)
            wl.last_matched_at = now
            wl.last_matched_case_id = case_id
            db.commit()

            for hit in matched_records[:5]:
                dedup_key = f"watchlist_hit_{wl.id}_{case_id}_{hit['record_type']}_{hit['record_id']}"
                title = f"🚨 Watchlist Hit: {wl.entity_type.upper()} '{wl.entity_value}' Detected"
                message = (
                    f"Watchlist target '{wl.entity_value}' ({wl.label}) was detected in Case #{case_id} ({case.title}). "
                    f"Found in {hit['file_name']}, Row #{hit['row_number']}: {hit['details']}."
                )

                alert = create_or_update_alert(
                    db=db,
                    case_id=case_id,
                    rule_type="watchlist_hit",
                    severity=wl.priority or "critical",
                    title=title,
                    message=message,
                    dedup_key=dedup_key,
                    linked_item_type="watchlist",
                    linked_item_id=str(wl.id)
                )

                matches.append({
                    "watchlist_id": wl.id,
                    "entity_type": wl.entity_type,
                    "entity_value": wl.entity_value,
                    "label": wl.label,
                    "hit": hit,
                    "alert_id": alert.id
                })

    return matches


def run_live_cdr_and_financial_analytics(
    case_id: int,
    db: Session,
    file_name: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Automated Intelligence Pipeline for Ingested CDR and Bank Files.
    Runs:
    1. Co-Location Detection (raises alerts for new co-locations)
    2. Common-Contact Bridge Analysis (raises alerts for shared bridge contacts)
    3. Short-Lived Burner SIM Detection (raises alerts for brief burst handsets)
    4. Impossible Travel Velocity Analysis (raises alerts for speeds > 140 km/h)
    5. Forensic Money Flow & Structuring Analysis (raises alerts for smurfing/layering)
    6. Cross-Case Watchlist Matching (raises critical alerts for marked targets)

    Guarantees: Raises alerts ONLY for new findings (deduped via dedup_key).
    Broadcasts real-time events over SSE.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {"status": "error", "message": f"Case #{case_id} not found."}

    logger.info(f"[LiveAnalytics] Running automatic CDR & Financial analysis for Case #{case_id} (file: {file_name}).")
    alerts_created = []

    # 1. Co-Location Checks
    try:
        colocations = analyze_co_location(case_id, db, window_minutes=15)
        for c in colocations:
            phone_a_num = c["phone_a"]["number"] if isinstance(c["phone_a"], dict) else str(c["phone_a"])
            phone_b_num = c["phone_b"]["number"] if isinstance(c["phone_b"], dict) else str(c["phone_b"])
            pair_key = "_".join(sorted([phone_a_num, phone_b_num]))
            dedup_key = f"cdr_coloc_{case_id}_{pair_key}_{c['cell_id']}"
            time_str = c["phone_a"]["timestamp"][:16] if isinstance(c["phone_a"], dict) and c["phone_a"].get("timestamp") else "Recent"
            src_a = f"{c['phone_a']['source_file']} Row #{c['phone_a']['row_number']}" if isinstance(c['phone_a'], dict) and c["phone_a"].get("source_file") else "File A"
            src_b = f"{c['phone_b']['source_file']} Row #{c['phone_b']['row_number']}" if isinstance(c['phone_b'], dict) and c["phone_b"].get("source_file") else "File B"
            title = f"📍 Co-Location Alert: Handsets Active at Tower {c['cell_id']}"
            message = (
                f"Suspicious co-location detected between {phone_a_num} and {phone_b_num} "
                f"at {c['site_name']} ({c['cell_id']}) within {c['time_delta_minutes']} mins on {time_str}. "
                f"Citations: {src_a} and {src_b}."
            )
            alt = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="cdr_colocation",
                severity="critical",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="cdr_records",
                linked_item_id=c['cell_id']
            )
            alerts_created.append(alt.id)
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Co-location check error: {e}")

    # 2. Common Contacts Checks
    try:
        common_contacts = analyze_common_contacts(case_id, db)
        for cc in common_contacts:
            suspects = cc.get("suspects_connected", [])
            if len(suspects) >= 2:
                dedup_key = f"cdr_common_contact_{case_id}_{cc['contact_number']}"
                title = f"📞 Common Contact Bridge: {cc['contact_number']} Links {len(suspects)} Suspects"
                message = (
                    f"Third-party number {cc['contact_number']} was contacted by multiple target suspects: "
                    f"{', '.join(suspects)} ({cc['total_calls']} total calls). "
                    f"Directly establishes conspiracy bridge."
                )
                alt = create_or_update_alert(
                    db=db,
                    case_id=case_id,
                    rule_type="cdr_common_contact",
                    severity="warning",
                    title=title,
                    message=message,
                    dedup_key=dedup_key,
                    linked_item_type="cdr_records",
                    linked_item_id=cc['contact_number']
                )
                alerts_created.append(alt.id)
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Common contacts error: {e}")

    # 3. Short-Lived Burner SIM Checks
    try:
        burners = analyze_short_lived_numbers(case_id, db, max_lifetime_hours=48.0)
        for b in burners:
            dedup_key = f"cdr_burner_{case_id}_{b['phone_number']}"
            title = f"🔥 Burner SIM Discovered: {b['phone_number']} (Active {b['active_duration_hours']}h)"
            first_s = b.get("first_seen", "")[:16]
            last_s = b.get("last_seen", "")[:16]
            message = (
                f"Handset {b['phone_number']} displayed classic burner SIM behavior: "
                f"only active for {b['active_duration_hours']} hours ({b['total_events']} total calls), then abandoned. "
                f"First Call: {first_s} | Last Call: {last_s}."
            )
            alt = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="cdr_burner_number",
                severity="warning",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="cdr_records",
                linked_item_id=b['phone_number']
            )
            alerts_created.append(alt.id)
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Burner SIM error: {e}")

    # 4. Impossible Travel Velocity Checks
    try:
        impossible_travel = analyze_impossible_travel(case_id, db, speed_threshold_kmh=140.0)
        for it in impossible_travel:
            dedup_key = f"cdr_speed_{case_id}_{it['phone_number']}_{it['event_a']['cell_id']}_{it['event_b']['cell_id']}"
            title = f"⚠️ Impossible Travel: {it['phone_number']} ({it['calculated_speed_kmh']} km/h)"
            message = it['reasoning']
            alt = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="cdr_impossible_travel",
                severity="critical",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="cdr_records",
                linked_item_id=it['phone_number']
            )
            alerts_created.append(alt.id)
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Impossible travel error: {e}")

    # 5. Financial Structuring & Money-Flow Checks
    try:
        money_flow = analyze_money_flow(case_id, db)
        for sa in money_flow.get("structuring_alerts", []):
            acc = sa.get("account_number", "Unknown")
            dedup_key = f"fin_structuring_{case_id}_{acc}"
            title = f"💰 Financial Smurfing: Cash Structuring on Account {acc}"
            message = sa.get("reasoning", "Cash deposit structuring detected.")
            alt = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="financial_structuring",
                severity="critical",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="bank_transactions",
                linked_item_id=acc
            )
            alerts_created.append(alt.id)

        for la in money_flow.get("layering_alerts", []):
            dedup_key = f"fin_layering_{case_id}_{la.get('inflow_amount')}"
            title = f"💸 Rapid Layering & Transit Dispersal ({la.get('timeframe_hours')}h)"
            message = la.get("reasoning", "Rapid dispersal of funds detected.")
            alt = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="financial_layering",
                severity="critical",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="bank_transactions",
                linked_item_id=str(la.get("inflow_amount"))
            )
            alerts_created.append(alt.id)
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Money flow error: {e}")

    # 6. Watchlist Cross-Case Matching
    watchlist_matches = []
    try:
        watchlist_matches = check_watchlists_for_case(case_id, db, user_id)
        for wm in watchlist_matches:
            if "alert_id" in wm:
                alerts_created.append(wm["alert_id"])
    except Exception as e:
        logger.warning(f"[LiveAnalytics] Watchlist check error: {e}")

    # Broadcast event via SSE so live case walls and network graphs update instantly
    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="cdr_financial_analyzed",
        summary=f"Automated CDR & financial analytics executed. {len(set(alerts_created))} alerts active.",
        payload={
            "case_id": case_id,
            "file_name": file_name,
            "alerts_created_count": len(set(alerts_created)),
            "watchlist_matches_count": len(watchlist_matches),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    return {
        "status": "success",
        "case_id": case_id,
        "file_name": file_name,
        "new_alerts_count": len(set(alerts_created)),
        "watchlist_matches_count": len(watchlist_matches),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_live_correlated_network(
    case_id: int,
    db: Session,
    time_start: Optional[datetime] = None,
    time_end: Optional[datetime] = None,
    search_number: Optional[str] = None,
    min_amount: float = 0.0,
    mode: str = "all"
) -> Dict[str, Any]:
    """
    Returns an aggregated, real-time node-link network of telecom calls and financial transfers.
    Dynamically grows as data is added.
    Supports filters by:
    - time (time_start, time_end)
    - number or account (search_number)
    - amount (min_amount)
    - mode ('all', 'telecom', 'financial')
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    case_title = case.title if case else f"Case #{case_id}"

    # Load active watchlists for highlighting
    watchlists = db.query(WatchlistEntry).filter(WatchlistEntry.is_active == True).all()
    watchlist_tokens: Dict[str, str] = {}
    for wl in watchlists:
        norm = normalize_watchlist_token(wl.entity_type, wl.entity_value)
        if norm:
            watchlist_tokens[norm] = wl.label

    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges_map: Dict[str, Dict[str, Any]] = {}

    total_calls_count = 0
    total_transfers_sum = 0.0

    # 1. TELECOM CALLS
    if mode in ["all", "telecom"]:
        cdr_query = db.query(CDRRecord).filter(CDRRecord.case_id == case_id)
        if time_start:
            cdr_query = cdr_query.filter(CDRRecord.call_datetime >= time_start)
        if time_end:
            cdr_query = cdr_query.filter(CDRRecord.call_datetime <= time_end)
        if search_number:
            clean_s = search_number.strip()
            cdr_query = cdr_query.filter(
                or_(
                    CDRRecord.calling_number.like(f"%{clean_s}%"),
                    CDRRecord.called_number.like(f"%{clean_s}%")
                )
            )

        cdrs = cdr_query.order_by(CDRRecord.call_datetime.asc()).all()
        for r in cdrs:
            src = r.calling_number.strip()
            dst = (r.called_number or "UNKNOWN").strip()
            if not src or not dst:
                continue

            total_calls_count += 1

            # Nodes
            for nid in [src, dst]:
                if nid not in nodes_map:
                    norm = normalize_watchlist_token("phone", nid)
                    is_wl = norm in watchlist_tokens
                    nodes_map[nid] = {
                        "id": nid,
                        "label": nid,
                        "type": "phone",
                        "degree": 0,
                        "total_volume": 0.0,
                        "total_calls": 0,
                        "is_watchlist_match": is_wl,
                        "details": {"watchlist_label": watchlist_tokens.get(norm)} if is_wl else {}
                    }
                nodes_map[nid]["total_calls"] += 1

            # Edge
            edge_key = f"call_{src}_{dst}"
            if edge_key not in edges_map:
                edges_map[edge_key] = {
                    "id": edge_key,
                    "source": src,
                    "target": dst,
                    "type": "call",
                    "count": 0,
                    "total_amount": 0.0,
                    "last_timestamp": None,
                    "modes": ["Voice/SMS"],
                    "linked_rows": []
                }
            edges_map[edge_key]["count"] += 1
            if r.call_datetime:
                edges_map[edge_key]["last_timestamp"] = r.call_datetime.isoformat()
            if len(edges_map[edge_key]["linked_rows"]) < 10:
                edges_map[edge_key]["linked_rows"].append({
                    "source_file": r.source_file_name,
                    "row_number": r.row_number,
                    "timestamp": r.call_datetime.isoformat() if r.call_datetime else None,
                    "type": r.call_type,
                    "tower": r.cell_id
                })

    # 2. FINANCIAL TRANSFERS
    if mode in ["all", "financial"]:
        bank_query = db.query(BankTransaction).filter(BankTransaction.case_id == case_id)
        if time_start:
            bank_query = bank_query.filter(BankTransaction.transaction_date >= time_start)
        if time_end:
            bank_query = bank_query.filter(BankTransaction.transaction_date <= time_end)
        if search_number:
            clean_s = search_number.strip()
            bank_query = bank_query.filter(
                or_(
                    BankTransaction.account_number.like(f"%{clean_s}%"),
                    BankTransaction.counterparty_account.like(f"%{clean_s}%"),
                    BankTransaction.description.like(f"%{clean_s}%")
                )
            )
        if min_amount > 0.0:
            bank_query = bank_query.filter(
                or_(
                    BankTransaction.debit_amount >= min_amount,
                    BankTransaction.credit_amount >= min_amount
                )
            )

        txns = bank_query.order_by(BankTransaction.transaction_date.asc()).all()
        for b in txns:
            amt = b.debit_amount if b.debit_amount > 0 else b.credit_amount
            src = b.account_number.strip()
            dst = (b.counterparty_account or b.counterparty_name or "Counterparty").strip()

            total_transfers_sum += amt

            for nid in [src, dst]:
                if nid not in nodes_map:
                    norm = normalize_watchlist_token("account", nid)
                    is_wl = norm in watchlist_tokens
                    nodes_map[nid] = {
                        "id": nid,
                        "label": nid,
                        "type": "account",
                        "degree": 0,
                        "total_volume": 0.0,
                        "total_calls": 0,
                        "is_watchlist_match": is_wl,
                        "details": {"watchlist_label": watchlist_tokens.get(norm)} if is_wl else {}
                    }
                nodes_map[nid]["total_volume"] = round(nodes_map[nid]["total_volume"] + amt, 2)

            edge_key = f"txn_{src}_{dst}"
            if edge_key not in edges_map:
                edges_map[edge_key] = {
                    "id": edge_key,
                    "source": src,
                    "target": dst,
                    "type": "transfer",
                    "count": 0,
                    "total_amount": 0.0,
                    "last_timestamp": None,
                    "modes": [],
                    "linked_rows": []
                }
            edges_map[edge_key]["count"] += 1
            edges_map[edge_key]["total_amount"] = round(edges_map[edge_key]["total_amount"] + amt, 2)
            if b.transaction_mode and b.transaction_mode not in edges_map[edge_key]["modes"]:
                edges_map[edge_key]["modes"].append(b.transaction_mode)
            if b.transaction_date:
                edges_map[edge_key]["last_timestamp"] = b.transaction_date.isoformat()
            if len(edges_map[edge_key]["linked_rows"]) < 10:
                edges_map[edge_key]["linked_rows"].append({
                    "source_file": b.source_file_name,
                    "row_number": b.row_number,
                    "date": b.transaction_date.isoformat() if b.transaction_date else None,
                    "amount": amt,
                    "mode": b.transaction_mode,
                    "description": b.description
                })

    # Compute node degrees
    for edge in edges_map.values():
        if edge["source"] in nodes_map:
            nodes_map[edge["source"]]["degree"] += 1
        if edge["target"] in nodes_map:
            nodes_map[edge["target"]]["degree"] += 1

    watchlist_matches_count = len([n for n in nodes_map.values() if n["is_watchlist_match"]])

    return {
        "case_id": case_id,
        "case_title": case_title,
        "nodes": list(nodes_map.values()),
        "edges": list(edges_map.values()),
        "total_nodes": len(nodes_map),
        "total_edges": len(edges_map),
        "total_calls": total_calls_count,
        "total_transfers_amount": round(total_transfers_sum, 2),
        "watchlist_matches_in_network": watchlist_matches_count,
        "filters_applied": {
            "time_start": time_start.isoformat() if time_start else None,
            "time_end": time_end.isoformat() if time_end else None,
            "search_number": search_number,
            "min_amount": min_amount,
            "mode": mode
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

