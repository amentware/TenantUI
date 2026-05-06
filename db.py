import sqlite3

DB_PATH = "database.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Tenants ──────────────────────────────────────────────
def get_tenants(search="", page=1, per_page=15):
    offset = (page - 1) * per_page
    like = f"%{search}%"
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM TENANT WHERE NAME LIKE ? OR TENANT_ID LIKE ? OR COUNTRY LIKE ?",
            (like, like, like)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT TENANT_ID, NAME, TYPE, COUNTRY, STATUS, CREATED_AT
               FROM TENANT
               WHERE NAME LIKE ? OR TENANT_ID LIKE ? OR COUNTRY LIKE ?
               ORDER BY CREATED_AT DESC LIMIT ? OFFSET ?""",
            (like, like, like, per_page, offset)
        ).fetchall()
    return [dict(r) for r in rows], total

def get_tenant(tenant_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM TENANT WHERE TENANT_ID=?", (tenant_id,)).fetchone()
    return dict(row) if row else None

def update_tenant(tenant_id, data):
    with get_conn() as conn:
        conn.execute(
            "UPDATE TENANT SET NAME=?, TYPE=?, COUNTRY=?, STATUS=? WHERE TENANT_ID=?",
            (data['name'], data['type'], data['country'], data['status'], tenant_id)
        )

# ── SIP Rules ────────────────────────────────────────────
def get_sip_rules_for_tenant(tenant_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT M.MAPPING_ID, M.TENANT_ID, R.RULE_ID, M.DESCRIPTION as MAPPING_DESC,
                      R.DESCRIPTION as MASTER_DESC, R.RULE_ACTION, M.CALL_TYPE, 
                      S.SERVICE_TYPE, R.CARRIER_SEARCH_MODE,
                      R.B_PARTY_CARRIER_MAPPING_ID, R.MSRN_CARRIER_MAPPING_ID,
                      R.TENANT_CARRIER_MAPPING_ID, R.DEFAULT_CARRIER_LIST_ID, R.RECORDING_FLAG
               FROM TENANT_SIP_RULE_MAPPING M
               JOIN SIP_RULE_MASTER R ON M.RULE_ID = R.RULE_ID
               JOIN SERVICE_MASTER  S ON M.SERVICE_ID = S.SERVICE_ID
               WHERE M.TENANT_ID = ?
               ORDER BY R.RULE_ID""",
            (tenant_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def get_all_rules():
    with get_conn() as conn:
        rows = conn.execute("SELECT RULE_ID, DESCRIPTION, RULE_ACTION, CARRIER_SEARCH_MODE FROM SIP_RULE_MASTER ORDER BY RULE_ID").fetchall()
    return [dict(r) for r in rows]

def get_rule_details(rule_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM SIP_RULE_MASTER WHERE RULE_ID=?", (rule_id,)).fetchone()
    return dict(row) if row else None

def get_all_services():
    with get_conn() as conn:
        rows = conn.execute("SELECT SERVICE_ID, SERVICE_TYPE FROM SERVICE_MASTER").fetchall()
    return [dict(r) for r in rows]

def add_sip_rule(tenant_id, rule_id, call_type, service_id, description):
    import datetime
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO TENANT_SIP_RULE_MAPPING
                   (TENANT_ID, RULE_ID, DESCRIPTION, CALL_TYPE, SERVICE_ID, CREATED_AT)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tenant_id, rule_id, description, call_type, service_id,
                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
        return True, None
    except sqlite3.IntegrityError:
        return False, "Duplicate: this combination already exists for the tenant."

def delete_sip_rule(mapping_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM TENANT_SIP_RULE_MAPPING WHERE MAPPING_ID=?", (mapping_id,))

def create_and_map_rule(tenant_id, rule_data, call_type, service_id):
    import datetime
    conn = get_conn()
    try:
        with conn:
            # 1. Create the rule in SIP_RULE_MASTER (let RULE_ID autoincrement)
            cur = conn.execute(
                """INSERT INTO SIP_RULE_MASTER 
                   (DESCRIPTION, RULE_ACTION, CARRIER_SEARCH_MODE, 
                    B_PARTY_CARRIER_MAPPING_ID, MSRN_CARRIER_MAPPING_ID, 
                    TENANT_CARRIER_MAPPING_ID, DEFAULT_CARRIER_LIST_ID, RECORDING_FLAG)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (rule_data['description'], rule_data['rule_action'], 
                 rule_data['carrier_search_mode'], rule_data['b_party_id'], 
                 rule_data['msrn_id'], rule_data['tenant_carrier_id'], 
                 rule_data['default_cl_id'], rule_data['recording_flag'])
            )
            new_rule_id = cur.lastrowid
            
            # 2. Map it to the tenant
            conn.execute(
                """INSERT INTO TENANT_SIP_RULE_MAPPING
                   (TENANT_ID, RULE_ID, DESCRIPTION, CALL_TYPE, SERVICE_ID, CREATED_AT)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (tenant_id, new_rule_id, rule_data['mapping_desc'], 
                 call_type, service_id,
                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()

def get_rule_mapping(mapping_id):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT m.*, r.DESCRIPTION as MASTER_DESC, r.CARRIER_SEARCH_MODE,
                   r.B_PARTY_CARRIER_MAPPING_ID, r.MSRN_CARRIER_MAPPING_ID,
                   r.TENANT_CARRIER_MAPPING_ID, r.DEFAULT_CARRIER_LIST_ID,
                   r.RECORDING_FLAG
            FROM TENANT_SIP_RULE_MAPPING m
            JOIN SIP_RULE_MASTER r ON m.RULE_ID = r.RULE_ID
            WHERE m.MAPPING_ID = ?
        """, (mapping_id,)).fetchone()
        return dict(row) if row else None

def update_sip_rule(mapping_id, rule_id, description, call_type, service_id):
    with get_conn() as conn:
        try:
            conn.execute("""
                UPDATE TENANT_SIP_RULE_MAPPING
                SET RULE_ID = ?, DESCRIPTION = ?, CALL_TYPE = ?, SERVICE_ID = ?
                WHERE MAPPING_ID = ?
            """, (rule_id, description, call_type, service_id, mapping_id))
            conn.commit()
            return True, None
        except Exception as e:
            return False, str(e)
