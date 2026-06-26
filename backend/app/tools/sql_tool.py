import re
from sqlalchemy import create_engine, text
from langsmith import traceable
from app.auth.db_permissions import (
    get_schema_for_role,
    validate_query_permissions,
    inject_row_filters,
    validate_sql_safety
)
from app.llm.router import get_llm
from app.config import get_settings

import urllib.parse

def get_db_url():
    settings = get_settings()
    pwd = urllib.parse.quote_plus(settings.SUPABASE_DB_PASSWORD)
    # Use the IPv4 connection pooler string that you got from Supabase
    return f"postgresql://postgres.hmsdswtaszpgmzkqiaxe:{pwd}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

@traceable(name="sql_query_tool")
async def sql_query(question: str, user_id: str, user_role: str) -> str:
    """
    Query the SQL database for numbers, analytics, and records.
    Implements a 4-layer security model.
    """
    # LAYER 1: Get filtered schema
    schema = get_schema_for_role(user_role)
    if not schema:
        return "You do not have permission to access the database."
        
    # Generate SQL using LLM
    llm = get_llm()
    prompt = f"""You are a PostgreSQL expert. Given the user's question, write a SQL query to answer it.
Return ONLY the raw SQL query, no markdown, no explanation.

CRITICAL INSTRUCTION:
When writing the SELECT query, make sure to include any columns referenced in the WHERE filter conditions (such as prices, dates, active status, etc.) in the SELECT statement. This allows the user to see the actual values that justify why the rows were retrieved. For example, if filtering products by price > 1000, select both 'name' and 'price'.

If the user asks for data (like a specific column) that is NOT present in the provided schema, return EXACTLY the string: PERMISSION_DENIED

DATABASE SCHEMA:
{schema}

QUESTION: {question}
SQL QUERY:"""
    
    response = llm.invoke(prompt)
    content = response.content.strip()
    
    if content == "PERMISSION_DENIED":
        return "Permission Denied: You do not have permission to view the requested data fields."

    # Robustly extract SQL from markdown blocks if the LLM ignores the "no markdown" instruction
    match = re.search(r"```(?:sql)?\n?(.*?)\n?```", content, re.DOTALL | re.IGNORECASE)
    if match:
        generated_sql = match.group(1).strip()
    else:
        generated_sql = content.replace("```sql", "").replace("```", "").strip()
    
    # LAYER 2: Validate SQL Safety
    is_safe, safety_msg = validate_sql_safety(generated_sql)
    if not is_safe:
        from app.auth.security_logger import log_security_alert
        from app.auth import user_store
        user_info = user_store.get_user_by_id(user_id)
        user_name = user_info.get("full_name", "Unknown User") if user_info else "Unknown User"
        log_security_alert(question, user_id, user_role, user_name, "unauthorized_db_modify", f"Blocked SQL: {generated_sql} | Reason: {safety_msg}")
        return f"This operation is not permitted. I can only read and retrieve data from the database. I cannot insert, update, or delete records. (Reason: {safety_msg})"
        
    # LAYER 3: Check Role Permissions
    is_allowed, perm_msg = validate_query_permissions(generated_sql, user_role)
    if not is_allowed:
        from app.auth.security_logger import log_security_alert
        from app.auth import user_store
        user_info = user_store.get_user_by_id(user_id)
        user_name = user_info.get("full_name", "Unknown User") if user_info else "Unknown User"
        log_security_alert(question, user_id, user_role, user_name, "unauthorized_column_access", f"Blocked SQL: {generated_sql} | Reason: {perm_msg}")
        return f"Access Denied: {perm_msg}"
        
    # LAYER 4: Inject Row-Level Security Filters
    secure_sql = inject_row_filters(generated_sql, user_role, user_id)
    
    # Execute Query
    try:
        engine = create_engine(get_db_url())
        with engine.connect() as conn:
            result = conn.execute(text(secure_sql))
            rows = result.fetchall()
            
            if not rows:
                return "The query returned no results."
            
            # Format results
            formatted = "\n".join([str(row) for row in rows])
            return f"Database Results:\n{formatted}"
            
    except Exception as e:
        return f"⚠️ Database connection issue: {str(e)}"