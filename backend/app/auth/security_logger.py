import urllib.parse
import os
import csv
import urllib.request
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from app.config import get_settings

def log_security_alert(query: str, user_id: str, user_role: str, user_name: str, alert_type: str, details: str = ""):
    """Logs security incidents such as injections, out of scope attempts, or unauthorized database operations."""
    try:
        timestamp = datetime.utcnow().isoformat()
        
        # 1. Append to local CSV spreadsheet
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_dir = os.path.join(base_dir, "data")
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, "security_alerts.csv")
        file_exists = os.path.isfile(csv_path)
        
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "User ID", "User Name", "User Role", "Query", "Alert Type", "Details"])
            writer.writerow([timestamp, user_id, user_name, user_role, query, alert_type, details])
            
        # 2. Slack Webhook Notification
        slack_url = os.environ.get("SLACK_WEBHOOK_URL")
        if slack_url:
            try:
                payload = {
                    "text": f"🚨 *Security Alert Triggered* 🚨\n"
                            f"*Time:* {timestamp}\n"
                            f"*User:* {user_name} ({user_role})\n"
                            f"*Query:* `{query}`\n"
                            f"*Alert Type:* `{alert_type}`\n"
                            f"*Details:* {details}"
                }
                
                req = urllib.request.Request(
                    slack_url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                # Wait up to 2 seconds for Slack response so we don't block the request
                with urllib.request.urlopen(req, timeout=2) as resp:
                    print(f"Sent Slack alert, status: {resp.status}")
            except Exception as se:
                print(f"Failed to send Slack alert: {se}")
                
        # 3. LangSmith Metadata Enrichment
        try:
            import langsmith as ls
            rt = ls.get_current_run_tree()
            if rt:
                root_rt = rt
                while root_rt.parent_run:
                    root_rt = root_rt.parent_run
                root_rt.metadata["security_incident"] = True
                root_rt.metadata["user_name"] = user_name
                root_rt.metadata["user_role"] = user_role
                root_rt.metadata["user_intent"] = alert_type
                if root_rt.tags is None:
                    root_rt.tags = []
                if "security_alert" not in root_rt.tags:
                    root_rt.tags.append("security_alert")
        except Exception as le:
            print(f"Error updating LangSmith metadata: {le}")

        # 4. Save to Database
        settings = get_settings()
        if not settings.SUPABASE_DB_PASSWORD:
            print("Skipping security alert DB log: SUPABASE_DB_PASSWORD not set.")
            return
        
        pwd = urllib.parse.quote_plus(settings.SUPABASE_DB_PASSWORD)
        db_url = f"postgresql://postgres.hmsdswtaszpgmzkqiaxe:{pwd}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO security_alerts (query, user_id, user_role, user_name, alert_type, details)
                    VALUES (:query, :user_id, :user_role, :user_name, :alert_type, :details)
                """),
                {
                    "query": query,
                    "user_id": user_id,
                    "user_role": user_role,
                    "user_name": user_name,
                    "alert_type": alert_type,
                    "details": details
                }
            )
            conn.commit()
            print(f"Logged security alert to database: {alert_type}")
    except Exception as e:
        print(f"Error logging security alert: {str(e)}")
