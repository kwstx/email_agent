import sqlite3

def check_schema():
    conn = sqlite3.connect("data/prospects.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(company)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")
    conn.close()

if __name__ == "__main__":
    check_schema()
