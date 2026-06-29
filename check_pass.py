import sqlite3, bcrypt, sys
sys.path.insert(0, 'Version 1.5/src')
conn = sqlite3.connect('Version 1.5/data/stockpro.db')
c = conn.cursor()
c.execute('SELECT id, username, password FROM usuarios WHERE username = ?', ('admin',))
row = c.fetchone()
if row:
    print(f'Found admin: id={row[0]}')
    for pw in ['admin', 'admin123']:
        try:
            if bcrypt.checkpw(pw.encode(), row[2].encode()):
                print(f'  -> MATCHES: "{pw}"')
            else:
                print(f'  -> NO match: "{pw}"')
        except Exception as e:
            print(f'  -> Error with "{pw}": {e}')
else:
    print('User "admin" not found!')
    c.execute('SELECT id, username FROM usuarios')
    for r in c.fetchall():
        print(f'  User: id={r[0]}, username={r[1]}')
conn.close()
