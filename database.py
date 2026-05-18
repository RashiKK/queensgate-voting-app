import sqlite3

DB_NAME = "voting.db"


def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    # voters table now includes secret_code
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        voting_power INTEGER NOT NULL,
        secret_code TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        candidate_name TEXT NOT NULL,
        vote_count INTEGER DEFAULT 0,
        FOREIGN KEY(topic_id) REFERENCES topics(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voter_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        voter_name TEXT NOT NULL,
        votes_used INTEGER DEFAULT 0,
        FOREIGN KEY(topic_id) REFERENCES topics(id)
    )
    """)

    conn.commit()

    # Hardcoded voters + secret codes
    voters = [
        ("Mohammad Wasim", 2, "WSM2026"),
        ("Atiqur Rahman", 3, "ATQ2026"),
        ("Sazzadul Mitu", 2, "MITU2026"),
        ("Naihan Ahmed", 2, "NAIH2026"),
        ("Robin Raquibul Kamal", 2, "RBK2026"),
        ("Mohammad Sohel Solaiman", 2, "SOHEL2026"),
        ("Gazi Salah Uddin", 2, "GAZI2026"),
        ("Md Minhaz Chowdhury", 1, "MINHAZ2026"),
        ("Zahid Islam", 2, "ZAHID2026"),
        ("Muhammad M Islam", 2, "ISLAM2026")
    ]

    # Insert voters if missing
    for name, power, code in voters:
        cursor.execute("""
            INSERT OR IGNORE INTO voters (name, voting_power, secret_code)
            VALUES (?, ?, ?)
        """, (name, power, code))

    conn.commit()
    conn.close()