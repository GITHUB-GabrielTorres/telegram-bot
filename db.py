import sqlite3

DB_PATH = "finance.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            movement_date TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reference_values (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT OR IGNORE INTO reference_values (key, value) VALUES (?, ?)",
        [
            ("day", 0.0),
            ("pages", 0.0),
            ("course_hours", 0.0),
            ("podcast_hours", 0.0),
            ("bible_verses", 0.0),
            ("golden_training", 0.0),
        ],
    )
    

    conn.commit()
    conn.close()


def get_balances(conn) -> list[tuple[str, float]]:
    return conn.execute(
        """
        SELECT u.name, COALESCE(SUM(m.amount), 0)
        FROM users u
        LEFT JOIN movements m ON m.person = u.name
        GROUP BY u.name
        """
    ).fetchall()