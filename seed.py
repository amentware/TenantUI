import sqlite3
import random
from datetime import datetime, timedelta

def setup_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # === SCHEMA ===
    c.executescript('''
        DROP TABLE IF EXISTS TENANT_SIP_RULE_MAPPING;
        DROP TABLE IF EXISTS SIP_RULE_MASTER;
        DROP TABLE IF EXISTS SERVICE_MASTER;
        DROP TABLE IF EXISTS TENANT;

        CREATE TABLE IF NOT EXISTS TENANT (
            TENANT_ID   TEXT PRIMARY KEY,
            NAME        TEXT NOT NULL,
            TYPE        TEXT NOT NULL,
            COUNTRY     TEXT NOT NULL,
            STATUS      TEXT NOT NULL DEFAULT 'ACTIVE',
            CREATED_AT  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS SIP_RULE_MASTER (
            RULE_ID                     INTEGER PRIMARY KEY AUTOINCREMENT,
            DESCRIPTION                 TEXT NOT NULL,
            RULE_ACTION                 TEXT NOT NULL DEFAULT 'ALLOW',
            CARRIER_SEARCH_MODE         TEXT NOT NULL,
            B_PARTY_CARRIER_MAPPING_ID  TEXT,
            MSRN_CARRIER_MAPPING_ID     TEXT,
            TENANT_CARRIER_MAPPING_ID   TEXT,
            DEFAULT_CARRIER_LIST_ID     TEXT,
            RECORDING_FLAG              INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS SERVICE_MASTER (
            SERVICE_ID   TEXT PRIMARY KEY,
            SERVICE_TYPE TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS TENANT_SIP_RULE_MAPPING (
            MAPPING_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
            TENANT_ID   TEXT NOT NULL,
            RULE_ID     INTEGER NOT NULL,
            DESCRIPTION TEXT,
            CALL_TYPE   TEXT NOT NULL,
            SERVICE_ID  TEXT NOT NULL,
            CREATED_AT  TEXT NOT NULL,
            UNIQUE(TENANT_ID, RULE_ID, CALL_TYPE, SERVICE_ID),
            FOREIGN KEY (TENANT_ID)  REFERENCES TENANT(TENANT_ID),
            FOREIGN KEY (RULE_ID)    REFERENCES SIP_RULE_MASTER(RULE_ID),
            FOREIGN KEY (SERVICE_ID) REFERENCES SERVICE_MASTER(SERVICE_ID)
        );

        CREATE TABLE IF NOT EXISTS LIST_MASTER (
            LIST_ID     INTEGER PRIMARY KEY AUTOINCREMENT,
            LIST_NAME   TEXT NOT NULL,
            LIST_TYPE   TEXT NOT NULL -- BPARTY, MSRN, DEFAULT, TENANT
        );

        CREATE TABLE IF NOT EXISTS B_PARTY_LIST (
            PK_ID               INTEGER PRIMARY KEY AUTOINCREMENT,
            ID                  INTEGER NOT NULL,
            DESTINATION_NUMBER  TEXT NOT NULL,
            DESTINATION_TYPE    TEXT NOT NULL,
            FOREIGN KEY (ID) REFERENCES LIST_MASTER(LIST_ID)
        );

        CREATE TABLE IF NOT EXISTS MSRN_LIST (
            PK_ID               INTEGER PRIMARY KEY AUTOINCREMENT,
            ID                  INTEGER NOT NULL,
            MSRN                TEXT NOT NULL,
            MSRN_TYPE           TEXT NOT NULL,
            FOREIGN KEY (ID) REFERENCES LIST_MASTER(LIST_ID)
        );

        CREATE TABLE IF NOT EXISTS TENANT_GROUP (
            PK_ID       INTEGER PRIMARY KEY AUTOINCREMENT,
            ID          INTEGER NOT NULL,
            TENANT_ID   TEXT NOT NULL,
            FOREIGN KEY (ID) REFERENCES LIST_MASTER(LIST_ID)
        );
    ''')

    # === SEED: SERVICE_MASTER ===
    services = [
        ('1', 'MO'),
        ('2', 'MT'),
        ('3', 'TSAN'),
        ('4', 'CAPV2'),
    ]
    c.executemany(
        'INSERT OR IGNORE INTO SERVICE_MASTER (SERVICE_ID, SERVICE_TYPE) VALUES (?, ?)',
        services
    )

    # === SEED: SIP_RULE_MASTER (Matching User Image) ===
    # Using specific Rule IDs for initial seed to match image, but future ones will be auto
    rules = [
        (3001, 'SIP AS WHOLE SALE PSTN ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '306', 0),
        (3002, 'SIP AS LOOP BACK ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '307', 0),
        (3003, 'SIP AS BT ROUTE', 'ALLOW', 'BPARTY', '2002', '0', '0', '0', 0),
        (3004, 'SIP AS REC AND ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '308', 1),
        (3005, 'SIP AS ENGINE MOBILE ONNET ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '310', 0),
        (3006, 'SIP AS ENGINE MOBILE OFFNET ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '309', 0),
        (3007, 'SIP AS KPN NATIONAL MSRN ROUTE', 'ALLOW', 'MSRN', '0', '1001', '0', '0', 0),
        (3008, 'SIP AS EE MSRN ROUTE', 'ALLOW', 'MSRN', '0', '1002', '0', '0', 0),
        (3009, 'SIP AS IMS REC AND ROUTE', 'ALLOW', 'BPARTY', '2001', '0', '0', '0', 1),
        (3010, 'SIP AS BT MSRN REC AND ROUTE', 'ALLOW', 'MSRN', '0', '1005', '0', '0', 1),
        (3011, 'SIP AS KPN REC AND ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '311', 1),
        (3012, 'SIP AS IBASIS MSRN ROUTE', 'ALLOW', 'MSRN', '0', '1003', '0', '0', 0),
        (3013, 'SIP AS IRISTEL ONNET ROUTE', 'ALLOW', 'DEFAULT', '0', '0', '0', '313', 0),
    ]
    c.executemany(
        '''INSERT OR IGNORE INTO SIP_RULE_MASTER
           (RULE_ID, DESCRIPTION, RULE_ACTION, CARRIER_SEARCH_MODE,
            B_PARTY_CARRIER_MAPPING_ID, MSRN_CARRIER_MAPPING_ID,
            TENANT_CARRIER_MAPPING_ID, DEFAULT_CARRIER_LIST_ID, RECORDING_FLAG)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        rules
    )

    # === SEED: TENANT ===
    tenant_types    = ['ENTERPRISE', 'CARRIER', 'MVNO', 'RESELLER']
    tenant_statuses = ['ACTIVE', 'INACTIVE', 'SUSPENDED']
    countries       = ['IN', 'US', 'GB', 'DE', 'SG', 'AU', 'AE', 'JP']
    tenants = []
    for i in range(1, 51):
        created = (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d %H:%M:%S')
        tenants.append((
            f'TEN-{i:04d}',
            f'Tenant {i:04d} Corp',
            random.choice(tenant_types),
            random.choice(countries),
            random.choice(tenant_statuses),
            created
        ))
    c.executemany(
        '''INSERT OR IGNORE INTO TENANT
           (TENANT_ID, NAME, TYPE, COUNTRY, STATUS, CREATED_AT)
           VALUES (?, ?, ?, ?, ?, ?)''',
        tenants
    )

    # === SEED: TENANT_SIP_RULE_MAPPING ===
    call_types  = ['ONNET', 'OFFNET', 'ALLCALL']
    service_ids = ['SVC-MO', 'SVC-MT', 'SVC-TSAN']
    mappings = set()
    mapping_rows = []
    for i in range(1, 51):
        tenant_id = f'TEN-{i:04d}'
        num_rules = random.randint(2, 6)
        rule_ids_pool = random.sample([r[0] for r in rules], k=min(num_rules, len(rules)))
        for rule_id in rule_ids_pool:
            call_type  = random.choice(call_types)
            service_id = random.choice(service_ids)
            key = (tenant_id, rule_id, call_type, service_id)
            if key not in mappings:
                mappings.add(key)
                created = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Use a combined description for seed data
                rule_desc = next((r[1] for r in rules if r[0] == rule_id), "Rule")
                mapping_rows.append((tenant_id, rule_id, f"Mapping {rule_id}", call_type, service_id, created))

    c.executemany(
        '''INSERT OR IGNORE INTO TENANT_SIP_RULE_MAPPING
           (TENANT_ID, RULE_ID, DESCRIPTION, CALL_TYPE, SERVICE_ID, CREATED_AT)
           VALUES (?, ?, ?, ?, ?, ?)''',
        mapping_rows
    )

    # === SEED: LIST_MASTER & LISTS ===
    list_masters = [
        (101, 'UK B-PARTY LIST', 'BPARTY'),
        (201, 'NETHERLANDS MSRN', 'MSRN'),
        (202, 'UK MSRN', 'MSRN'),
        (306, 'GLOBAL DEFAULT CARRIER', 'DEFAULT'),
        (401, 'TENANT GROUP ALPHA', 'TENANT')
    ]
    c.executemany('INSERT OR IGNORE INTO LIST_MASTER (LIST_ID, LIST_NAME, LIST_TYPE) VALUES (?, ?, ?)', list_masters)

    b_party_details = [
        (101, '44794?%', 'SERIES'),
        (101, '44795?%', 'SERIES'),
        (101, '44796?%', 'SERIES')
    ]
    c.executemany('INSERT OR IGNORE INTO B_PARTY_LIST (ID, DESTINATION_NUMBER, DESTINATION_TYPE) VALUES (?, ?, ?)', b_party_details)

    msrn_details = [
        (201, '3165302?%', 'SERIES'),
        (201, '3165304?%', 'SERIES'),
        (202, '44795?%', 'SERIES')
    ]
    c.executemany('INSERT OR IGNORE INTO MSRN_LIST (ID, MSRN, MSRN_TYPE) VALUES (?, ?, ?)', msrn_details)

    tenant_group_details = [
        (401, 'TEN-0004')
    ]
    c.executemany('INSERT OR IGNORE INTO TENANT_GROUP (ID, TENANT_ID) VALUES (?, ?)', tenant_group_details)

    conn.commit()
    conn.close()
    print(f"Database seeded successfully: {len(tenants)} tenants, {len(rules)} rules, {len(mapping_rows)} mappings.")

if __name__ == '__main__':
    setup_database()
