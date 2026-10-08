import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
from report_generator import generate_case_pdf_report

db = SessionLocal()
try:
    print("Testing generate_case_pdf_report for Case 1...")
    pdf_bytes = generate_case_pdf_report(case_id=1, db=db)
    print(f"Generated PDF successfully! Size: {len(pdf_bytes):,} bytes")
    
    out_path = os.path.join(os.path.dirname(__file__), "sample_case_report.pdf")
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"Saved sample report to: {out_path}")
    assert len(pdf_bytes) > 5000, "PDF too small!"
    print("PDF Generation Verification Passed!")
finally:
    db.close()
