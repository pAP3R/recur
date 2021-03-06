import sqlite3
import uuid
import time

connection = sqlite3.connect('database.db')


with open('schema.sql') as f:
    connection.executescript(f.read())

######
# Setup for testing, this entry is just to populate the DB so it has something immediately.
#
#cur = connection.cursor()
#print(time.time())
#next_run = time.time() + 604800
#cur.execute("INSERT INTO recurring_orders (created, last_run, next_run, side, asset, quantity, frequency, active, exchange, type, uuid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#        (time.time(), time.time(), next_run, 'buy', 'BTC-USD', '25.00', 'Weekly', 'Active', 'Gemini', 'Market', str(uuid.uuid4()))
#        )


print("DB Done!")

connection.commit()
connection.close()
