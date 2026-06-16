import os, sys
os.chdir('Version 1.2')
from dotenv import load_dotenv
load_dotenv()

from src.app import app as real_app
from src import database as db

conn = db.obtener_conexion()
cursor = conn.cursor()
cursor.execute("SELECT id FROM usuarios WHERE username = 'testadmin'")
if not cursor.fetchone():
    from src.database import hash_password
    cursor.execute("INSERT INTO usuarios (username, password, nombre, email, rol, activo) VALUES (?, ?, ?, ?, ?, ?)",
        ('testadmin', hash_password('test123'), 'Test Admin', 'test@test.com', 'admin', 1))
    conn.commit()
conn.close()

with real_app.test_client() as client:
    resp = client.post('/login', data={'username': 'testadmin', 'password': 'test123'}, follow_redirects=True)
    resp = client.get('/analisis')
    print('Status:', resp.status_code)
    content = resp.data.decode('utf-8')
    print('Content length:', len(content))
    print('Has KPIs:', 'total-productos' in content)
    print('Has charts:', 'ventasChart' in content)
    print('Has tables:', 'abc-body' in content)
    print('Has errors:', 'Error cargando' in content or 'Traceback' in content)
    print('Has PDF:', 'exportarPDF' in content)
    print('Has CSV:', 'exportarCSV' in content)
    # Print first 2000 chars to see what's happening
    print('---FIRST 2000 CHARS---')
    print(content[:2000])
