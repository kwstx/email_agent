import sqlite3

def check_field():
    conn = sqlite3.connect("data/prospects.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(company)")
    columns = [row[1] for row in cursor.fetchall()]
    if "fitness_level" in columns:
        print("YES, fitness_level exists")
    else:
        print("NO, fitness_level MISSING")
    
    if "fitness_score" in columns:
        print("YES, fitness_score exists")
    else:
        print("NO, fitness_score MISSING")
    conn.close()

if __name__ == "__main__":
    check_field()
