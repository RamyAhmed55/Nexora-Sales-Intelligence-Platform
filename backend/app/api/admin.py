import urllib.parse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from app.dependencies import get_current_user
from app.auth.jwt_handler import UserContext
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

def get_db_engine():
    settings = get_settings()
    if not settings.SUPABASE_DB_PASSWORD:
        raise HTTPException(status_code=500, detail="Database connection password is not configured.")
    pwd = urllib.parse.quote_plus(settings.SUPABASE_DB_PASSWORD)
    db_url = f"postgresql://postgres.hmsdswtaszpgmzkqiaxe:{pwd}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
    return create_engine(db_url)

@router.get("/security-alerts")
def get_security_alerts(user: UserContext = Depends(get_current_user)):
    if user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can access security logs.")
        
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, query, user_id, user_role, user_name, alert_type, details, created_at
                FROM security_alerts
                ORDER BY created_at DESC
                LIMIT 100
            """)).fetchall()
            
            alerts = []
            for row in result:
                alerts.append({
                    "id": str(row[0]),
                    "query": row[1],
                    "user_id": row[2],
                    "user_role": row[3],
                    "user_name": row[4],
                    "alert_type": row[5],
                    "details": row[6] or "",
                    "created_at": row[7].isoformat() if row[7] else ""
                })
            return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")