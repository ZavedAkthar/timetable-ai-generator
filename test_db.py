from utils.helpers import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT DATABASE(), VERSION()")
print(cursor.fetchone())
cursor.close()
conn.close()
