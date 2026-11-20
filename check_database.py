print("Checking database...")

import sqlite3

with sqlite3.connect('case_charm.db') as conn:
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", cursor.fetchall())

    cursor.execute("SELECT * FROM orders")
    print("Saved orders:", cursor.fetchall())


