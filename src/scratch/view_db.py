import sqlite3

DB_PATH = r"C:\Users\Varsha\OneDrive\Documents\Github\AgentTeam\workspace\agentteam.db"  # Change if needed

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name;
""")

tables = cursor.fetchall()

if not tables:
    print("No tables found.")
    exit()

for (table_name,) in tables:
    print("\n" + "=" * 80)
    print(f"TABLE: {table_name}")
    print("=" * 80)

    # Print column names
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    columns = [col[1] for col in cursor.fetchall()]
    print("Columns:", columns)

    # Print rows
    cursor.execute(f'SELECT * FROM "{table_name}"')
    rows = cursor.fetchall()

    print(f"Rows: {len(rows)}\n")

    for row in rows:
        print(row)

conn.close()
