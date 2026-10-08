import os
import shutil
from pathlib import Path

src_base = Path("d:/Avadhut/project/Evidentia-AI-main/Evidentia-AI-main")
dest_bases = [
    Path("D:/Avadhut/project/major/new v2/Evidentia-AI-main"),
    Path("D:/Avadhut/project/major/new/Evidentia-AI-main/Evidentia-AI-main")
]

files = [
    "backend/auth.py",
    "backend/audit_engine.py",
    "backend/storage.py",
    "backend/models.py",
    "backend/schemas.py",
    "backend/citation_engine.py",
    "backend/report_generator.py",
    "backend/app.py",
    "backend/evidentia.db",
    "src/types/index.ts",
    "src/services/index.ts",
    "src/context/AuthContext.tsx",
    "src/pages/global/Login.tsx",
    "src/components/layout/Topbar.tsx",
    "src/components/common/SourceSpanViewerModal.tsx",
    "src/pages/global/Cases.tsx",
    "src/pages/case/CaseOverview.tsx",
    "src/pages/case/EvidenceList.tsx",
    "src/pages/case/EvidenceDetails.tsx",
    "src/pages/case/Hypotheses.tsx",
    "src/pages/case/CaseReports.tsx",
    "src/pages/case/ActivityLog.tsx",
    "src/App.tsx",
    "scratch/migrate_feature3.py",
    "scratch/test_feature3_backend.py",
    "scratch/test_feature4_backend.py"
]


for dest in dest_bases:
    if dest.exists():
        print(f"Syncing to destination: {dest}")
        for rel in files:
            sf = src_base / rel
            df = dest / rel
            if sf.exists():
                df.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sf, df)
                print(f"  Copied: {rel}")
            else:
                print(f"  Source not found: {sf}")
    else:
        print(f"Destination does not exist, skipping: {dest}")

print("Sync completed successfully.")
