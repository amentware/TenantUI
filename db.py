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
                      R.TENANT_CARRIER_MAPPING_ID, R.DEFAULT_CARRIER_LIST_ID, R.RECORDING_FLAG,
                      C.DESCRIPTION as CARRIER_NAME
               FROM TENANT_SIP_RULE_MAPPING M
               JOIN SIP_RULE_MASTER R ON M.RULE_ID = R.RULE_ID
               JOIN SERVICE_MASTER  S ON M.SERVICE_ID = S.SERVICE_ID
               LEFT JOIN CARRIER_MASTER C ON M.CARRIER_ID = C.CARRIER_ID
               WHERE M.TENANT_ID = ?
               ORDER BY R.RULE_ID""",
            (tenant_id,)
        ).fetchall()
        
        # Helper to get names for comma-separated IDs
        all_lists = {str(l['LIST_ID']): l['LIST_NAME'] for l in get_all_lists()}
        
        results = []
        for r in rows:
            rd = dict(r)
            
            def get_names(id_str):
                if not id_str or id_str == '0': return "N/A"
                ids = id_str.split(",")
                return ", ".join([all_lists.get(i.strip(), i.strip()) for i in ids if i.strip()])
            
            rd['B_PARTY_LIST_NAME'] = get_names(rd['B_PARTY_CARRIER_MAPPING_ID'])
            rd['MSRN_LIST_NAME'] = get_names(rd['MSRN_CARRIER_MAPPING_ID'])
            rd['TENANT_LIST_NAME'] = get_names(rd['TENANT_CARRIER_MAPPING_ID'])
            rd['DEFAULT_LIST_NAME'] = get_names(rd['DEFAULT_CARRIER_LIST_ID'])
            
            results.append(rd)
            
    return results

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

def add_sip_rule(tenant_id, rule_id, call_type, service_id, carrier_id, description):
    import datetime
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO TENANT_SIP_RULE_MAPPING
                   (TENANT_ID, RULE_ID, DESCRIPTION, CALL_TYPE, SERVICE_ID, CARRIER_ID, CREATED_AT)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (tenant_id, rule_id, description, call_type, service_id, carrier_id,
                 datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
        return True, None
    except sqlite3.IntegrityError:
        return False, "Duplicate: this combination already exists for the tenant."

def delete_sip_rule(mapping_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM TENANT_SIP_RULE_MAPPING WHERE MAPPING_ID=?", (mapping_id,))

def create_and_map_rule(tenant_id, rule_data, call_type, service_id, carrier_id):
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
                   (TENANT_ID, RULE_ID, DESCRIPTION, CALL_TYPE, SERVICE_ID, CARRIER_ID, CREATED_AT)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (tenant_id, new_rule_id, rule_data['mapping_desc'], 
                 call_type, service_id, carrier_id,
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

def update_sip_rule_full(mapping_id, rule_id, description, call_type, service_id, carrier_id, master_data):
    with get_conn() as conn:
        try:
            # 1. Update Mapping
            conn.execute("""
                UPDATE TENANT_SIP_RULE_MAPPING
                SET RULE_ID = ?, DESCRIPTION = ?, CALL_TYPE = ?, SERVICE_ID = ?, CARRIER_ID = ?
                WHERE MAPPING_ID = ?
            """, (rule_id, description, call_type, service_id, carrier_id, mapping_id))
            
            # 2. Update Master Rule (associated with this mapping)
            conn.execute("""
                UPDATE SIP_RULE_MASTER
                SET CARRIER_SEARCH_MODE = ?, B_PARTY_CARRIER_MAPPING_ID = ?, 
                    MSRN_CARRIER_MAPPING_ID = ?, TENANT_CARRIER_MAPPING_ID = ?, 
                    DEFAULT_CARRIER_LIST_ID = ?, RECORDING_FLAG = ?
                WHERE RULE_ID = ?
            """, (master_data['carrier_search_mode'], master_data['b_party_id'],
                  master_data['msrn_id'], master_data['tenant_carrier_id'],
                  master_data['default_cl_id'], master_data['recording_flag'], rule_id))
            
            conn.commit()
            return True, None
        except Exception as e:
            return False, str(e)

# ── List Management ─────────────────────────────────────
def get_all_lists(list_type=None):
    with get_conn() as conn:
        if list_type:
            rows = conn.execute("SELECT * FROM LIST_MASTER WHERE LIST_TYPE = ?", (list_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM LIST_MASTER").fetchall()
    return [dict(r) for r in rows]

def get_all_carriers():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM CARRIER_MASTER ORDER BY DESCRIPTION").fetchall()
    return [dict(r) for r in rows]

def create_list(name, list_type, details):
    """
    details is a list of tuples/dicts depending on type:
    BPARTY: [(destination_number, destination_type), ...]
    MSRN: [(msrn, msrn_type), ...]
    TENANT: [tenant_id, ...]
    """
    with get_conn() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO LIST_MASTER (LIST_NAME, LIST_TYPE) VALUES (?, ?)", (name, list_type))
            list_id = cursor.lastrowid
            
            if list_type == 'BPARTY':
                for d_num, d_type in details:
                    cursor.execute("INSERT INTO B_PARTY_LIST (ID, DESTINATION_NUMBER, DESTINATION_TYPE) VALUES (?, ?, ?)", (list_id, d_num, d_type))
            elif list_type == 'MSRN':
                for msrn, msrn_type in details:
                    cursor.execute("INSERT INTO MSRN_LIST (ID, MSRN, MSRN_TYPE) VALUES (?, ?, ?)", (list_id, msrn, msrn_type))
            elif list_type == 'TENANT':
                for t_id in details:
                    cursor.execute("INSERT INTO TENANT_GROUP (ID, TENANT_ID) VALUES (?, ?)", (list_id, t_id))
            
            conn.commit()
            return True, list_id
        except Exception as e:
            conn.rollback()
            return False, str(e)

def get_list_details(list_id, list_type):
    with get_conn() as conn:
        if list_type == 'BPARTY':
            rows = conn.execute("SELECT * FROM B_PARTY_LIST WHERE ID = ?", (list_id,)).fetchall()
        elif list_type == 'MSRN':
            rows = conn.execute("SELECT * FROM MSRN_LIST WHERE ID = ?", (list_id,)).fetchall()
        elif list_type == 'TENANT':
            rows = conn.execute("SELECT * FROM TENANT_GROUP WHERE ID = ?", (list_id,)).fetchall()
        else:
            return []
    return [dict(r) for r in rows]
