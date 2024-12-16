import sqlite3

def test_db_connection():
    try:
        conn = sqlite3.connect('pix_store1.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    test_db_connection()
