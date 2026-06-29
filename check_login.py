import sqlite3, bcrypt
conn = sqlite3.connect('Version 1.5/data/stockpro.db')
c = conn.cursor()
c.execute('SELECT username, password FROM usuarios WHERE username = ?', ('admin',))
row = c.fetchone()
print(f'User: {row[0]}')
print(f'Hash: {row[1][:30]}...')
try:
    r1 = bcrypt.checkpw(b'admin123', row[1].encode())
    print(f'admin123: {r1}')
except Exception as e:
    print(f'admin123 error: {e}')
try:
    r2 = bcrypt.checkpw(b'admin', row[1].encode())
    print(f'admin: {r2}')
except Exception as e:
    print(f'admin error: {e}')
conn.close()
