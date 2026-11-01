"""
Unit and Integration Tests for CDR and Forensic Financial Analytics.

Validates:
1. Multi-format Parsers (CSV & Excel) for CDR and Tower-Dumps with 1-based row tracking.
2. Co-Location Detection: Handsets in the same sector within a configurable time window with dual-row citations.
3. Common Contacts Discovery: Shared bridge conspirator numbers across suspects with row citations.
4. Short-Lived / Burner Numbers: Disposable SIM detection based on active lifetime and call volume.
5. Impossible Travel / Velocity Anomalies: Flagging physical teleportation (>160 km/h) with dual-row citations.
6. Bank Statement Importer & Directed Money-Flow Graph: Account nodes, directed edges, smurfing & layering detection.
"""

import io
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import openpyxl

from database import Base
from models import Case, Evidence, User, CDRRecord, BankTransaction
from cdr_financial_engine import (
    parse_and_store_cdr,
    parse_and_store_bank_statement,
    analyze_co_location,
    analyze_common_contacts,
    analyze_short_lived_numbers,
    analyze_impossible_travel,
    analyze_money_flow,
    haversine_distance_km
)


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    case = Case(
        title="State of Maharashtra vs. Raut & Gang",
        description="High-profile abduction, robbery, and murder investigation.",
        status="Active",
        fir_number="FIR-2009-PUNE-01",
        created_by="Director"
    )
    session.add(case)
    session.commit()

    yield session
    session.close()


# ==============================================================================
# TEST 1: CDR PARSERS (CSV & EXCEL) WITH EXACT ROW LINKAGE
# ==============================================================================

def test_parse_cdr_csv_with_row_linkage(db_session):
    csv_data = """Calling No,Called No,Call Time,Duration Sec,Cell ID,Site Name
+91-98200-44911,9811002233,2026-04-30 21:00:00,45,CELL-KHARADI-01,Kharadi Bypass Sector 4
9820044911,+91-98330-99881,2026-04-30 21:15:00,120,CELL-KHARADI-01,Kharadi Bypass Sector 4
+91-98765-43210,9811002233,2026-04-30 21:05:00,30,CELL-KHARADI-01,Kharadi Bypass Sector 4
"""
    res = parse_and_store_cdr(
        file_content=csv_data.encode("utf-8"),
        file_name="telecom_cdr_dump.csv",
        case_id=1,
        evidence_id=101,
        db=db_session
    )
    assert res["parsed_records"] == 3
    assert res["unique_phone_numbers"] >= 3

    # Verify rows stored in database with exact 1-based line row_number
    records = db_session.query(CDRRecord).filter(CDRRecord.case_id == 1).order_by(CDRRecord.row_number).all()
    assert len(records) == 3

    # Row 2 (first data line after header)
    assert records[0].row_number == 2
    assert records[0].calling_number == "+919820044911"
    assert records[0].cell_id == "CELL-KHARADI-01"
    assert records[0].call_duration_sec == 45
    assert records[0].source_file_name == "telecom_cdr_dump.csv"

    # Row 3
    assert records[1].row_number == 3
    assert records[1].calling_number == "+919820044911"
    assert records[1].called_number == "+919833099881"

    # Row 4
    assert records[2].row_number == 4
    assert records[2].calling_number == "+919876543210"


def test_parse_cdr_excel_with_openpyxl(db_session):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["A_Party", "B_Party", "Timestamp", "Duration", "Tower_ID", "Azimuth"])
    ws.append(["9820044911", "9899001122", "2026-04-30 22:00:00", 60, "CELL-YERWADA-01", 120])
    ws.append(["9899001122", "9820044911", "2026-04-30 22:30:00", 15, "CELL-YERWADA-01", 120])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = parse_and_store_cdr(
        file_content=buf.getvalue(),
        file_name="tower_dump_airtel.xlsx",
        case_id=1,
        evidence_id=102,
        db=db_session
    )
    assert res["parsed_records"] == 2

    records = db_session.query(CDRRecord).filter(CDRRecord.source_file_name == "tower_dump_airtel.xlsx").all()
    assert len(records) == 2
    assert records[0].row_number == 2
    assert records[0].azimuth == 120.0
    assert records[1].row_number == 3


# ==============================================================================
# TEST 2: CO-LOCATION DETECTION WITH DUAL FILE ROW CITATIONS
# ==============================================================================

def test_co_location_detection(db_session):
    # Two different suspect handsets active at same cell tower at 21:00 and 21:06 (6 mins delta)
    r1 = CDRRecord(
        case_id=1,
        evidence_id=1,
        source_file_name="cdr_suspect_raut.csv",
        row_number=14,
        calling_number="+919820044911",
        called_number="+919811002233",
        call_datetime=datetime(2026, 4, 30, 21, 0, 0, tzinfo=timezone.utc),
        call_duration_sec=40,
        cell_id="CELL-KHARADI-01",
        site_name="Kharadi Bypass Sector 4, Pune",
        latitude=18.5518,
        longitude=73.9352
    )
    r2 = CDRRecord(
        case_id=1,
        evidence_id=2,
        source_file_name="cdr_suspect_thakur.csv",
        row_number=28,
        calling_number="+919876543210",
        called_number="+919899001122",
        call_datetime=datetime(2026, 4, 30, 21, 6, 0, tzinfo=timezone.utc),
        call_duration_sec=55,
        cell_id="CELL-KHARADI-01",
        site_name="Kharadi Bypass Sector 4, Pune",
        latitude=18.5518,
        longitude=73.9352
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    colocations = analyze_co_location(case_id=1, db=db_session, window_minutes=15)
    assert len(colocations) == 1
    event = colocations[0]

    assert event["cell_id"] == "CELL-KHARADI-01"
    assert event["time_delta_minutes"] == 6.0
    assert event["confidence"] >= 90.0

    # Strict citation verification for BOTH phones
    assert event["phone_a"]["number"] == "+919820044911"
    assert event["phone_a"]["row_number"] == 14
    assert event["phone_a"]["source_file"] == "cdr_suspect_raut.csv"

    assert event["phone_b"]["number"] == "+919876543210"
    assert event["phone_b"]["row_number"] == 28
    assert event["phone_b"]["source_file"] == "cdr_suspect_thakur.csv"
    assert "Row #14" in event["reasoning"] and "Row #28" in event["reasoning"]


# ==============================================================================
# TEST 3: COMMON CONTACTS DISCOVERY WITH SOURCE ROW AUDITING
# ==============================================================================

def test_common_contacts_discovery(db_session):
    # Suspect Raut (+919820044911) calls Bridge Contact (+919811002233) on Row 5
    # Suspect Thakur (+919876543210) calls Bridge Contact (+919811002233) on Row 19
    r1 = CDRRecord(
        case_id=1,
        source_file_name="exhibit_cdr_01.csv",
        row_number=5,
        calling_number="+919820044911",
        called_number="+919811002233",
        call_datetime=datetime(2026, 4, 30, 19, 0, 0, tzinfo=timezone.utc),
        call_duration_sec=90,
        cell_id="CELL-KHARADI-01"
    )
    r2 = CDRRecord(
        case_id=1,
        source_file_name="exhibit_cdr_02.csv",
        row_number=19,
        calling_number="+919876543210",
        called_number="+919811002233",
        call_datetime=datetime(2026, 4, 30, 19, 30, 0, tzinfo=timezone.utc),
        call_duration_sec=110,
        cell_id="CELL-YERWADA-01"
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    common = analyze_common_contacts(case_id=1, db=db_session, suspect_numbers=["+919820044911", "+919876543210"])
    assert len(common) == 1
    bridge = common[0]

    assert bridge["contact_number"] == "+919811002233"
    assert bridge["suspects_connected_count"] == 2
    assert set(bridge["suspects_connected"]) == {"+919820044911", "+919876543210"}
    assert bridge["total_calls"] == 2

    # Check row citations
    rows = bridge["all_linked_rows"]
    assert len(rows) == 2
    row_nums = {r["row_number"] for r in rows}
    assert 5 in row_nums and 19 in row_nums


# ==============================================================================
# TEST 4: SHORT-LIVED / BURNER SIM DETECTION
# ==============================================================================

def test_short_lived_burner_number_detection(db_session):
    # Disposable SIM active for only 3.5 hours on Row 12, 13, 14, then silent
    base_time = datetime(2026, 4, 30, 20, 0, 0, tzinfo=timezone.utc)
    burner_recs = [
        CDRRecord(
            case_id=1,
            source_file_name="cdr_burner_seizure.csv",
            row_number=12,
            calling_number="+919999000011",
            called_number="+919820044911",
            call_datetime=base_time,
            call_duration_sec=30,
            cell_id="CELL-KHARADI-01"
        ),
        CDRRecord(
            case_id=1,
            source_file_name="cdr_burner_seizure.csv",
            row_number=13,
            calling_number="+919999000011",
            called_number="+919876543210",
            call_datetime=base_time + timedelta(hours=1.5),
            call_duration_sec=45,
            cell_id="CELL-KHARADI-01"
        ),
        CDRRecord(
            case_id=1,
            source_file_name="cdr_burner_seizure.csv",
            row_number=14,
            calling_number="+919999000011",
            called_number="+919811002233",
            call_datetime=base_time + timedelta(hours=3.5),
            call_duration_sec=20,
            cell_id="CELL-YERWADA-01"
        ),
    ]
    db_session.add_all(burner_recs)
    db_session.commit()

    burners = analyze_short_lived_numbers(case_id=1, db=db_session, max_lifetime_hours=72.0)
    assert len(burners) >= 1
    target = next((b for b in burners if b["phone_number"] == "+919999000011"), None)
    assert target is not None
    assert target["active_duration_hours"] == 3.5
    assert target["total_events"] == 3
    assert len(target["linked_rows"]) == 3
    assert {r["row_number"] for r in target["linked_rows"]} == {12, 13, 14}


# ==============================================================================
# TEST 5: IMPOSSIBLE TRAVEL VELOCITY ANOMALIES
# ==============================================================================

def test_impossible_travel_velocity_anomaly(db_session):
    # Pune Kharadi (18.5518, 73.9352) at 21:00 (Row #2)
    # Mumbai CST (18.9402, 72.8356) at 21:20 (Row #3) -> ~123.6 km in 20 mins = 370.9 km/h!
    t1 = datetime(2026, 4, 30, 21, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 30, 21, 20, 0, tzinfo=timezone.utc)

    r1 = CDRRecord(
        case_id=1,
        source_file_name="cloned_sim_investigation.csv",
        row_number=2,
        calling_number="+919820044911",
        call_datetime=t1,
        cell_id="CELL-KHARADI-01",
        site_name="Kharadi Bypass Sector 4, Pune",
        latitude=18.5518,
        longitude=73.9352
    )
    r2 = CDRRecord(
        case_id=1,
        source_file_name="cloned_sim_investigation.csv",
        row_number=3,
        calling_number="+919820044911",
        call_datetime=t2,
        cell_id="TOWER-MUM-CST-01",
        site_name="Chhatrapati Shivaji Maharaj Terminus, Mumbai",
        latitude=18.9402,
        longitude=72.8356
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    anomalies = analyze_impossible_travel(case_id=1, db=db_session, speed_threshold_kmh=160.0)
    assert len(anomalies) >= 1
    anom = anomalies[0]

    assert anom["phone_number"] == "+919820044911"
    assert anom["calculated_speed_kmh"] > 350.0
    assert anom["distance_km"] > 120.0
    assert anom["time_delta_minutes"] == 20.0
    assert anom["event_a"]["row_number"] == 2
    assert anom["event_b"]["row_number"] == 3
    assert "Physically Impossible Speed" in anom["reasoning"]


# ==============================================================================
# TEST 6: BANK STATEMENT IMPORTER & MONEY-FLOW GRAPH
# ==============================================================================

def test_bank_statement_import_and_money_flow(db_session):
    stmt_csv = """Txn Date,Description,Ref No,Debit,Credit,Balance
2026-04-28,UPI/34125/P2P/payee_logistics,UPI-34125,48500.00,,151500.00
2026-04-29,UPI/34126/P2P/payee_logistics,UPI-34126,49000.00,,102500.00
2026-04-30,NEFT-HDFC001-HAWALA AGENT-A/C 5010099,NEFT-9911,,250000.00,352500.00
2026-04-30,IMPS/P2A/412/DISPERSAL ACC 8881,IMPS-412,200000.00,,152500.00
"""
    res = parse_and_store_bank_statement(
        file_content=stmt_csv.encode("utf-8"),
        file_name="sbi_current_account_statement.csv",
        case_id=1,
        evidence_id=201,
        db=db_session,
        account_number_hint="SBIN00044911"
    )
    assert res["parsed_transactions"] == 4
    assert res["total_debit"] == 297500.0
    assert res["total_credit"] == 250000.0

    # Run Money-Flow Analysis
    flow = analyze_money_flow(case_id=1, db=db_session)
    assert flow["total_transactions"] == 4
    assert len(flow["nodes"]) >= 3
    assert len(flow["edges"]) >= 2

    # Verify edge row citations
    for edge in flow["edges"]:
        assert len(edge["linked_rows"]) >= 1
        for row in edge["linked_rows"]:
            assert row["row_number"] in [2, 3, 4, 5]
            assert row["source_file"] == "sbi_current_account_statement.csv"

    # Verify Structuring / Smurfing Alert (Rows 2 & 3: ₹48,500 and ₹49,000 just under ₹50,000 threshold)
    assert len(flow["structuring_alerts"]) >= 1
    alert = flow["structuring_alerts"][0]
    assert alert["alert_type"] == "smurfing_threshold_evasion"
    assert alert["matched_transactions_count"] == 2
    assert {r["row_number"] for r in alert["linked_rows"]} == {2, 3}

    # Verify Layering Alert (Inflow of ₹2,50,000 on Row 4 followed by ₹2,00,000 dispersal on Row 5)
    assert len(flow["layering_alerts"]) >= 1
    layering = flow["layering_alerts"][0]
    assert layering["alert_type"] == "rapid_layering_passthrough"
    assert layering["inflow_row"]["row_number"] == 4
    assert layering["outflow_rows"][0]["row_number"] == 5

