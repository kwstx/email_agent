import sqlite3

def check_employee_count():
    conn = sqlite3.connect("data/prospects.db")
    cursor = conn.cursor()
    cursor.execute("SELECT domain, employee_count FROM company WHERE employee_count IS NOT NULL LIMIT 10")
    rows = cursor.fetchall()
    
    if rows:
        print(f"Found {len(rows)} companies with employee_count:")
        for row in rows:
            print(f"  {row[0]}: {row[1]}")
    else:
        print("No companies with employee_count found yet.")
    
    conn.close()

if __name__ == "__main__":
    check_employee_count()
