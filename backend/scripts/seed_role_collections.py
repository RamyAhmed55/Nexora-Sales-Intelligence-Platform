import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ingestion.pipeline import ingest_document

ROLE_DOCS = {
    "public_policy.md": {
        "access_roles": ["public"],
        "content": "# Nexora General Welcome & Public Policy\nStandard business hours are 9 AM to 5 PM, Monday through Friday.\nOur head office is located at 100 Innovation Way, Tech District.\nAll employees must log their attendance in the portal daily.\n"
    },
    "sales_playbook.md": {
        "access_roles": ["sales"],
        "content": "# Nexora Confidential Sales Playbook\nStandard discount limit is 15% for Sales Reps.\nAny discount above 15% requires written approval from a regional manager.\nFor enterprise clients (deals above $50k), consult the custom quote sheet.\n"
    },
    "support_manual.md": {
        "access_roles": ["support"],
        "content": "# Internal Support Runbook & RMA Manual\nRMA hardware process must be initiated within 14 days of customer request.\nAlways verify the serial number in the system before generating a prepaid shipping label.\nFor firmware mismatches, perform a hard reset by holding power for 10 seconds.\n"
    },
    "manager_strategy.md": {
        "access_roles": ["manager"],
        "content": "# Nexora Management Strategy & Budgets\nQ3 department expansion budget is $250,000.\nWe plan to hire 3 new sales representatives and 2 support engineers this quarter.\nSalary ranges for junior sales reps should be capped at $65,000 base.\n"
    },
    "admin_system.md": {
        "access_roles": ["admin"],
        "content": "# Nexora Administrator Operations Guide\nMaster database backup rotation occurs every 24 hours at 02:00 UTC.\nAPI keys for third-party billing providers must be rotated on the first Monday of every quarter.\nIn the event of a cluster failure, redirect traffic to the secondary standby node.\n"
    }
}

def seed_role_collections():
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "seed_documents")
    os.makedirs(docs_dir, exist_ok=True)
    for filename, data in ROLE_DOCS.items():
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data["content"])
        result = ingest_document(
            file_path=filepath,
            file_type="text/markdown",
            access_roles=data["access_roles"],
            document_type="policy",
            uploaded_by="system",
            doc_id=filename.replace(".md", "")
        )
        print(f"Ingested {filename} to {result['collections']}")

if __name__ == "__main__":
    seed_role_collections()