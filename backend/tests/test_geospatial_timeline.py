"""
backend/tests/test_geospatial_timeline.py
=========================================
Automated unit and integration test suite verifying the Real-Time Timeline and Map:
1. Multi-layer spatio-temporal data aggregation (CDR Towers, CCTV Sightings, Witness Statements, Physical Artifacts).
2. Visual Uncertainty:
   - Temporal: time uncertainty window (time_window_start, time_window_end, time_uncertainty_minutes)
   - Spatial: cellular tower sector radial cones (azimuth, beam_width, radius_meters) vs witness area vs CCTV pinpoint.
3. Impossible travel detection (> 140 km/h anomaly flagging with trajectory vector).
4. Source provenance attribution (exhibit name, exact quote, character offsets, hash verification).
5. Real-time event simulation endpoint triggering live SSE broadcast.
6. RBAC access enforcement.
"""

from datetime import datetime, timezone, timedelta
import pytest

from models import Case, CaseMember, Evidence, Event, CDRRecord


@pytest.fixture
def geo_test_case(db, seed_users):
    """Sets up a comprehensive case with real CDR and Event records for geospatial testing."""
    lead = seed_users["lead_investigator"]
    case = Case(
        title="Geospatial Telemetry Test Investigation",
        description="Pune-Mumbai Corridor Spatio-Temporal Tracking Trial",
        fir_number="FIR-2026-GEO-001",
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

    # Add backing evidence exhibit
    ev = Evidence(
        case_id=case.id,
        file_name="cell_cctv_dump.pdf",
        storage_path="uploads/cell_cctv_dump.pdf",
        file_type="application/pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evidence_type="CDR",
        hash_verified=True,
        sec_65b_certificate_present=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # 1. Event 1: CCTV sighting at Kharadi Bypass (pinpoint, 20:30)
    e1 = Event(
        case_id=case.id,
        title="Silver Indica Passing Kharadi Octroi Post",
        description="High-definition ANPR camera captured vehicle MH-12-AR-4091 heading east toward Wagholi",
        timestamp=datetime(2026, 10, 15, 20, 30, 0, tzinfo=timezone.utc),
        location="Kharadi Bypass Octroi Post, Pune",
        latitude=18.5529,
        longitude=73.9422,
        event_type="cctv_sighting",
        time_uncertainty_minutes=2,
        confidence=0.98,
        evidence_id=ev.id,
        source_quote="ANPR Frame #4810 confirmed silver Indica MH-12-AR-4091 at 20:30:04",
        source_char_start=410,
        source_char_end=482,
        source_page_number=4,
    )
    db.add(e1)

    # 2. Event 2: Witness statement with temporal uncertainty (21:10 - 21:40)
    e2 = Event(
        case_id=case.id,
        title="Witness Statement: Tea Stall Vendor at Wagholi Phata",
        description="Witness heard loud argument near idling cab between 9:10 PM and 9:40 PM",
        timestamp=datetime(2026, 10, 15, 21, 25, 0, tzinfo=timezone.utc),
        location="Wagholi Phata Highway Dhaba, Pune",
        latitude=18.5793,
        longitude=73.9789,
        event_type="witness_report",
        time_uncertainty_minutes=20,
        confidence=0.75,
        evidence_id=ev.id,
        source_quote="Around 9:15 to 9:35 PM I noticed a silver cab stopped near the canal turnoff with lights switched off",
        source_char_start=812,
        source_char_end=925,
        source_page_number=7,
    )
    db.add(e2)

    # 3. CDR Record 1: Kharadi Tower Sector 2 (Azimuth 120°) at 20:35
    cdr1 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="cell_cctv_dump.pdf",
        row_number=142,
        calling_number="+919820011111",
        called_number="+919820022222",
        call_datetime=datetime(2026, 10, 15, 20, 35, 0, tzinfo=timezone.utc),
        call_duration_sec=95,
        call_type="voice",
        cell_id="PUN-KHD-04B",
        azimuth=120.0,
        site_name="Kharadi Bypass BTS Sector 2",
        latitude=18.5535,
        longitude=73.9398,
        imei="867530901234567",
        imsi="404450123456789",
    )
    db.add(cdr1)

    # 4. CDR Record 2: Wagholi Tower Sector 1 (Azimuth 60°) at 21:05
    cdr2 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="cell_cctv_dump.pdf",
        row_number=188,
        calling_number="+919820011111",
        called_number="+919820033333",
        call_datetime=datetime(2026, 10, 15, 21, 5, 0, tzinfo=timezone.utc),
        call_duration_sec=42,
        call_type="voice",
        cell_id="PUN-WGH-01A",
        azimuth=60.0,
        site_name="Wagholi Highway Tower Sector 1",
        latitude=18.5810,
        longitude=73.9850,
        imei="867530901234567",
        imsi="404450123456789",
    )
    db.add(cdr2)

    # 5. CDR Record 3: Impossible Travel Anomaly - Mumbai CST at 21:30 (125 km away in 25 mins = 300 km/h)
    cdr3 = CDRRecord(
        case_id=case.id,
        evidence_id=ev.id,
        source_file_name="cell_cctv_dump.pdf",
        row_number=215,
        calling_number="+919820011111",
        called_number="+919820099999",
        call_datetime=datetime(2026, 10, 15, 21, 30, 0, tzinfo=timezone.utc),
        call_duration_sec=18,
        call_type="sms",
        cell_id="MUM-CST-08",
        azimuth=270.0,
        site_name="Chhatrapati Shivaji Maharaj Terminus Tower 3",
        latitude=18.9400,
        longitude=72.8350,
        imei="867530901234567",
        imsi="404450123456789",
    )
    db.add(cdr3)

    db.commit()
    return case


def test_get_geospatial_timeline_aggregates_layers(client, geo_test_case, lead_headers):
    """Verifies that CDR towers, CCTV sightings, and witness statements are unified into one dataset."""
    resp = client.get(
        f"/cases/{geo_test_case.id}/geospatial-timeline",
        headers=lead_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == geo_test_case.id
    assert "time_horizon" in data
    assert data["total_points_count"] >= 4

    # Check presence of distinct layers
    geo_types = {pt["geo_type"] for pt in data["points"]}
    assert "tower_sector" in geo_types
    assert "point" in geo_types

    types = {pt["type"] for pt in data["points"]}
    assert "cdr_ping" in types
    assert "cctv_sighting" in types


def test_visual_uncertainty_attributes(client, geo_test_case, lead_headers):
    """Verifies spatial sectors (azimuth, beam_width, radius) and temporal ranges are computed."""
    resp = client.get(
        f"/cases/{geo_test_case.id}/geospatial-timeline",
        headers=lead_headers,
    )
    assert resp.status_code == 200
    points = resp.json()["points"]

    tower_points = [p for p in points if p["geo_type"] == "tower_sector"]
    assert len(tower_points) >= 2
    for tp in tower_points:
        assert tp["azimuth"] is not None
        assert tp["beam_width"] is not None
        assert tp["radius_meters"] > 0

    # Check witness / uncertain event temporal window
    uncertain_events = [p for p in points if p.get("time_uncertainty_minutes", 0) > 0]
    assert len(uncertain_events) >= 1
    ue = uncertain_events[0]
    assert ue["time_uncertainty_minutes"] > 0


def test_impossible_travel_detection(client, geo_test_case, lead_headers):
    """Verifies that speed exceeding 140 km/h between Wagholi and Mumbai is flagged as impossible travel."""
    resp = client.get(
        f"/cases/{geo_test_case.id}/geospatial-timeline",
        headers=lead_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    anomalies = data.get("impossible_travel_anomalies", [])
    assert len(anomalies) >= 1

    first_anomaly = anomalies[0]
    assert first_anomaly["calculated_speed_kmh"] > 140
    assert first_anomaly["distance_km"] > 50
    assert len(first_anomaly["from_coords"]) == 2
    assert len(first_anomaly["to_coords"]) == 2


def test_source_provenance_and_quote_extraction(client, geo_test_case, lead_headers):
    """Verifies that clicking any point yields backing exhibit reference and verified quote/row."""
    resp = client.get(
        f"/cases/{geo_test_case.id}/geospatial-timeline",
        headers=lead_headers,
    )
    assert resp.status_code == 200
    points = resp.json()["points"]

    cctv_point = next(p for p in points if p["type"] == "cctv_sighting")
    assert cctv_point["source_quote"] is not None
    assert "MH-12" in cctv_point["source_quote"] or "Indica" in cctv_point["source_quote"]
    assert cctv_point["hash_verified"] is True
    assert cctv_point["source_page_or_row"] is not None

    cdr_point = next(p for p in points if p["type"] == "cdr_ping")
    assert cdr_point["source_evidence_name"] == "cell_cctv_dump.pdf"
    assert cdr_point["source_page_or_row"] in [142, 188, 215]


def test_simulate_live_geospatial_event(client, geo_test_case, lead_headers):
    """Verifies the live simulation endpoint broadcasts an SSE event and adds to timeline."""
    resp = client.post(
        f"/cases/{geo_test_case.id}/geospatial-timeline/simulate-event",
        headers=lead_headers,
        json={
            "title": "Live Toll Plaza ANPR Hit MH-12-AR-4091",
            "description": "Vehicle crossed Talegaon Toll Plaza outbound towards Pune Expressway",
            "latitude": 18.7230,
            "longitude": 73.6820,
            "event_type": "cctv_sighting",
            "timestamp": "2026-10-15T22:15:00Z",
            "source_quote": "Talegaon Toll Plaza Lane 3 Sensor triggered: MH-12-AR-4091 at 22:15:10",
        },
    )
    assert resp.status_code == 200
    sim_data = resp.json()
    assert sim_data["status"] == "published"
    assert sim_data["point"]["latitude"] == 18.7230
    assert sim_data["point"]["geo_type"] == "point"


def test_geospatial_timeline_rbac_unauthorized(client, geo_test_case, reviewer_headers):
    """Verifies that an unassigned user is blocked from viewing geospatial telemetry."""
    resp = client.get(
        f"/cases/{geo_test_case.id}/geospatial-timeline",
        headers=reviewer_headers,
    )
    assert resp.status_code == 403
