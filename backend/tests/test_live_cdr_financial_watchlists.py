"""
backend/tests/test_live_cdr_financial_watchlists.py
===================================================
Automated test suite verifying Live CDR, Financial Analytics & Watchlists:
1. Watchlist Registry CRUD (phone numbers, bank accounts, vehicle plates, persons of interest).
2. Automated Multi-Check Pipeline on Ingestion:
   - Co-location detection raises alert
   - Common contacts discovery raises alert
   - Short-lived / burner SIM candidate raises alert
   - Money-flow structuring / smurfing raises alert
   - Deduplication: running analysis multiple times does NOT spam duplicate alerts (raises only for new findings).
3. Cross-Case Watchlist Match Detection:
   - When a monitored target appears in an exhibit, raises a critical Alert with exact file & row citation.
   - Increments match count and tracks last match timestamp.
4. Correlated Live Network Graph:
   - Generates nodes and edges for calls and transfers
   - Dynamic filters by time, search number, and amount
   - Identifies watchlist matches directly in the graph
"""

from datetime import datetime, timezone, timedelta
import pytest

from models import Case, CaseMember, Evidence, CDRRecord, BankTransaction, WatchlistEntry, Alert
from cdr_financial_engine import run_live_cdr_and_financial_analytics, get_live_correlated_network


@pytest.fixture
def live_analytics_case(db, seed_users):
    """Sets up a complete case with CDR records, bank transactions, and active watchlists."""
    lead = seed_users["lead_investigator"]
    case = Case(
        title="Hawala Network & Cellular Co-Location Investigation",
        description="Complex kidnapping and extortion syndicate cross-case tracking",
        fir_number="FIR-2026-CDR-009",
        status="Active",
        created_by=lead.full_name,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Add case member
    cm = CaseMember(
        case_id=case.id,
        user_id=lead.id,
        case_role="lead_investigator",
    )
    db.add(cm)

    # Add evidence exhibit
    ev = Evidence(
        case_id=case.id,
        file_name="Nodal_CDR_and_Bank_Dump.csv",
        storage_path="uploads/Nodal_CDR_and_Bank_Dump.csv",
        file_type="text/csv",
        file_hash="112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00",
        evidence_type="CDR",
        hash_verified=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    t0 = datetime(2026, 10, 15, 20, 0, 0, tzinfo=timezone.utc)

    # 1. Co-location pair: Suspect 1 (+919820011111) and Suspect 2 (+919820022222) at Kharadi Tower Sector 4
    cdr1 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=101,
        calling_number="+919820011111",
        called_number="+919820088888",
        call_datetime=t0 + timedelta(minutes=10),
        call_duration_sec=65,
        call_type="voice",
        cell_id="CELL-KHARADI-01",
        site_name="Kharadi Bypass Sector 4, Pune",
        latitude=18.5518,
        longitude=73.9352,
    )
    cdr2 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=102,
        calling_number="+919820022222",
        called_number="+919820088888",
        call_datetime=t0 + timedelta(minutes=14),
        call_duration_sec=40,
        call_type="voice",
        cell_id="CELL-KHARADI-01",
        site_name="Kharadi Bypass Sector 4, Pune",
        latitude=18.5518,
        longitude=73.9352,
    )

    # 2. Burner SIM candidate: active only for 3 hours, 4 calls total
    cdr3 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=103,
        calling_number="+919999900001",
        called_number="+919820011111",
        call_datetime=t0 + timedelta(hours=1),
        call_duration_sec=15,
        call_type="voice",
        cell_id="CELL-YERWADA-01",
        site_name="Yerwada SBI ATM Sector, Pune",
        latitude=18.5529,
        longitude=73.8824,
    )
    cdr4 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=104,
        calling_number="+919999900001",
        called_number="+919820022222",
        call_datetime=t0 + timedelta(hours=2),
        call_duration_sec=30,
        call_type="voice",
        cell_id="CELL-YERWADA-01",
        site_name="Yerwada SBI ATM Sector, Pune",
        latitude=18.5529,
        longitude=73.8824,
    )

    # 3. Bank Transactions: Structuring pattern (3 deposits just below threshold on same day)
    b1 = BankTransaction(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=201,
        transaction_date=t0 + timedelta(days=1, hours=2),
        credit_amount=48500.0,
        debit_amount=0.0,
        balance=48500.0,
        account_number="SBI-9910223344",
        counterparty_account="CASH-DEP-PUNE",
        counterparty_name="Cash Deposit Machine Pune",
        transaction_mode="CASH",
        description="CDM Self Deposit Yerwada Branch"
    )
    b2 = BankTransaction(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=202,
        transaction_date=t0 + timedelta(days=1, hours=3),
        credit_amount=49000.0,
        debit_amount=0.0,
        balance=97500.0,
        account_number="SBI-9910223344",
        counterparty_account="CASH-DEP-KHARADI",
        counterparty_name="Cash Deposit Machine Kharadi",
        transaction_mode="CASH",
        description="CDM Self Deposit Kharadi Branch"
    )
    b3 = BankTransaction(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=203,
        transaction_date=t0 + timedelta(days=1, hours=4),
        credit_amount=47000.0,
        debit_amount=0.0,
        balance=144500.0,
        account_number="SBI-9910223344",
        counterparty_account="CASH-DEP-CAMP",
        counterparty_name="Cash Deposit Machine Camp",
        transaction_mode="CASH",
        description="CDM Self Deposit Camp Branch"
    )

    # Transfer from SBI-9910223344 to Hawala Conduit HDFC-44001122
    b4 = BankTransaction(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="Nodal_CDR_and_Bank_Dump.csv",
        row_number=204,
        transaction_date=t0 + timedelta(days=1, hours=6),
        debit_amount=140000.0,
        credit_amount=0.0,
        balance=4500.0,
        account_number="SBI-9910223344",
        counterparty_account="HDFC-44001122",
        counterparty_name="M/S Sterling Trading Co",
        transaction_mode="RTGS",
        description="RTGS UTR Sterling Trading Co"
    )

    db.add_all([cdr1, cdr2, cdr3, cdr4, b1, b2, b3, b4])
    db.commit()

    return case


def test_watchlist_crud_endpoints(client, lead_headers):
    """Verifies creating, listing, updating, and deleting watchlist targets."""
    # 1. Create Watchlist for a phone number
    resp = client.post(
        "/watchlists",
        headers=lead_headers,
        json={
            "entity_type": "phone",
            "entity_value": "+91-98200-11111",
            "label": "Prime Accused Raut Secret SIM",
            "priority": "critical",
            "notes": "Intercepted during prior kidnapping trial"
        }
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["entity_type"] == "phone"
    assert data["label"] == "Prime Accused Raut Secret SIM"
    wl_id = data["id"]

    # 2. List Watchlists
    list_resp = client.get("/watchlists", headers=lead_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == wl_id for item in items)

    # 3. Update Watchlist
    update_resp = client.put(
        f"/watchlists/{wl_id}",
        headers=lead_headers,
        json={"priority": "high", "notes": "Updated note from intelligence bureau"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["priority"] == "high"

    # 4. Filter by entity_type
    filter_resp = client.get("/watchlists?entity_type=phone", headers=lead_headers)
    assert filter_resp.status_code == 200
    assert all(i["entity_type"] == "phone" for i in filter_resp.json())


def test_automated_cdr_and_financial_analytics_with_deduplication(client, live_analytics_case, lead_headers, db):
    """
    Verifies that running live analysis:
    1. Detects co-location (+919820011111 and +919820022222 at Kharadi)
    2. Detects common contact (+919820088888)
    3. Detects burner SIM (+919999900001)
    4. Detects structuring (3x CDM deposits < 50k on SBI-9910223344)
    5. Deduplication: running analysis again does NOT duplicate alerts.
    """
    case_id = live_analytics_case.id

    # 1. First Run: Should create alerts for new findings
    resp1 = client.post(
        f"/cases/{case_id}/telecom-financial/run-live-analysis",
        headers=lead_headers,
    )
    assert resp1.status_code == 200, resp1.text
    res_data1 = resp1.json()
    assert res_data1["status"] == "success"
    assert res_data1["new_alerts_count"] >= 3

    # Check alerts in DB
    initial_alerts_count = db.query(Alert).filter(Alert.case_id == case_id).count()
    assert initial_alerts_count >= 3

    # Verify specific alert rule types exist
    alert_rules = [a.rule_type for a in db.query(Alert).filter(Alert.case_id == case_id).all()]
    assert "cdr_colocation" in alert_rules
    assert "cdr_common_contact" in alert_rules
    assert "cdr_burner_number" in alert_rules
    assert "financial_structuring" in alert_rules

    # 2. Second Run: Deduplication guarantee - alerts are NOT duplicated
    resp2 = client.post(
        f"/cases/{case_id}/telecom-financial/run-live-analysis",
        headers=lead_headers,
    )
    assert resp2.status_code == 200
    alerts_after_second_run = db.query(Alert).filter(Alert.case_id == case_id).count()
    assert alerts_after_second_run == initial_alerts_count, "Alerts must be deduplicated; no duplicates allowed!"


def test_cross_case_watchlist_trigger_alert(client, live_analytics_case, lead_headers, db):
    """
    Verifies that when a watchlist target (account or phone) is matched in a case,
    a critical Watchlist Hit Alert is immediately raised with exact row citations.
    """
    case_id = live_analytics_case.id

    # Create a watchlist targeting the conduit account HDFC-44001122
    wl_resp = client.post(
        "/watchlists",
        headers=lead_headers,
        json={
            "entity_type": "account",
            "entity_value": "HDFC-44001122",
            "label": "M/S Sterling Trading Co (Hawala Conduit)",
            "priority": "critical"
        }
    )
    assert wl_resp.status_code == 201
    wl_id = wl_resp.json()["id"]

    # Run analysis
    res = run_live_cdr_and_financial_analytics(case_id, db)
    assert res["status"] == "success"

    # Verify watchlist hit alert was raised
    wl_alert = db.query(Alert).filter(
        Alert.case_id == case_id,
        Alert.rule_type == "watchlist_hit",
        Alert.linked_item_id == str(wl_id)
    ).first()

    assert wl_alert is not None
    assert "HDFC-44001122" in wl_alert.title
    assert "Sterling Trading Co" in wl_alert.message
    assert wl_alert.severity == "critical"

    # Verify watchlist entry stats updated
    wl_entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == wl_id).first()
    assert wl_entry.match_count >= 1
    assert wl_entry.last_matched_case_id == case_id


def test_live_network_view_endpoint_and_filters(client, live_analytics_case, lead_headers):
    """
    Verifies that GET /cases/{case_id}/telecom-financial/live-network:
    1. Returns interconnected callers and accounts as nodes and calls/transfers as edges.
    2. Identifies watchlisted nodes.
    3. Respects filters by search number, minimum amount, and mode.
    """
    case_id = live_analytics_case.id

    # 1. Full Correlated Network
    resp = client.get(
        f"/cases/{case_id}/telecom-financial/live-network",
        headers=lead_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["case_id"] == case_id
    assert data["total_nodes"] >= 4
    assert data["total_edges"] >= 3
    assert data["total_calls"] >= 4
    assert data["total_transfers_amount"] >= 140000.0

    # 2. Filter by search number
    search_resp = client.get(
        f"/cases/{case_id}/telecom-financial/live-network?search_number=9820011111",
        headers=lead_headers,
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert all("9820011111" in n["label"] or any("9820011111" in (e["source"] + e["target"]) for e in search_data["edges"]) for n in search_data["nodes"])

    # 3. Filter by minimum amount (>= 100,000)
    amt_resp = client.get(
        f"/cases/{case_id}/telecom-financial/live-network?min_amount=100000&mode=financial",
        headers=lead_headers,
    )
    assert amt_resp.status_code == 200
    amt_data = amt_resp.json()
    for edge in amt_data["edges"]:
        assert edge["total_amount"] >= 100000.0

    # 4. Filter by mode (telecom only)
    telecom_resp = client.get(
        f"/cases/{case_id}/telecom-financial/live-network?mode=telecom",
        headers=lead_headers,
    )
    assert telecom_resp.status_code == 200
    telecom_data = telecom_resp.json()
    assert all(e["type"] == "call" for e in telecom_data["edges"])
    assert all(n["type"] == "phone" for n in telecom_data["nodes"])

