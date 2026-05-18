import sqlite3

DB_NAME = "voting.db"


# ================= CONNECT =================
def connect_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ================= INIT DB =================
def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    # ================= USERS (VOTERS) =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        voting_power INTEGER NOT NULL,
        password TEXT NOT NULL,
        must_change_password INTEGER DEFAULT 1
    )
    """)

    # ================= TOPICS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    # ================= VOTES =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        candidate_name TEXT NOT NULL,
        vote_count INTEGER DEFAULT 0
    )
    """)

    # ================= VOTER USAGE =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voter_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        voter_email TEXT NOT NULL,
        votes_used INTEGER DEFAULT 0
    )
    """)

    conn.commit()

    # ================= DEFAULT USERS =================
    # IMPORTANT:
    # password = temporary password (first login)
    voters = [
    ("Atiqur Rahman", "atiq1512rahman@yahoo.com", 3, "ATQ2026"),
    ("Mohammad Wasim", "md_wasim03@yahoo.com", 2, "WSM2026"),
    ("Sazzadul Mitu", "Mitu.rc@gmail.com", 2, "MITU2026"),
    ("Naihan Ahmed", "naihanahmed@msn.com", 2, "NAIH2026"),
    ("Robin Kamal", "robinrkamal@gmail.com", 2, "RBK2026"),
    ("Sohel Solaiman", "sohel.solaiman@gmail.com", 2, "SOHEL2026"),
    ("Gazi Salah Uddin", "Shumon905@gmail.com", 2, "GAZI2026"),
    ("Minhaz Chowdhury", "minhazc@gmail.com", 1, "MINHAZ2026"),
    ("Zahid Islam", "sajib27@yahoo.com", 2, "ZAHID2026"),
    ("Muhammad M Islam", "fsmi1255@gmail.com", 2, "ISLAM2026")
]

    for name, email, power, pwd in voters:
        cursor.execute("""
        INSERT OR IGNORE INTO voters
        (name, email, voting_power, password, must_change_password)
        VALUES (?, ?, ?, ?, 1)
        """, (name, email, power, pwd))

    conn.commit()
    conn.close()