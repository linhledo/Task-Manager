import psycopg

connection = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="postgres",
    user="postgres",
    password="2006"
)

cursor = connection.cursor()

cursor.execute("SELECT * FROM users")

users = cursor.fetchall()

print(users)

connection.close()
cursor.close()