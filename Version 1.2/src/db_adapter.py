import os
import re
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL', '')
USING_PG = DATABASE_URL.startswith('postgresql')

class IntegrityError(Exception):
    pass


def get_connection():
    if DATABASE_URL.startswith('postgresql'):
        return _PGConnection()
    conn = sqlite3.connect(_get_db_path(), timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _get_db_path():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'data', 'stockpro.db'
    )


class _PGConnection:
    def __init__(self):
        import psycopg2
        import psycopg2.extras
        self._conn = psycopg2.connect(DATABASE_URL)
        self._conn.autocommit = True

    def cursor(self):
        return _PGCursor(self._conn)

    def execute(self, sql, params=None):
        sql = self._convert(sql)
        cur = self._conn.cursor()
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        cur.close()
        return cur

    def commit(self):
        pass

    def close(self):
        self._conn.close()

    @staticmethod
    def _convert(sql):
        s = sql.strip()
        if s.upper().startswith('PRAGMA'):
            return 'SELECT 1'
        s = re.sub(r"date\('now',\s*'start\s+of\s+month'\)",
                    "date_trunc('month', CURRENT_DATE)::date", s)
        s = re.sub(r"date\('now',\s*'(-?\d+)\s+months'\)",
                   r"(CURRENT_DATE + INTERVAL '\1 months')::date", s)
        s = re.sub(r"date\('now',\s*'\+?(\d+)\s+days'\)",
                   r"(CURRENT_DATE + INTERVAL '\1 days')::date", s)
        s = re.sub(r"date\('now',\s*'-(\d+)\s+days'\)",
                   r"(CURRENT_DATE - INTERVAL '\1 days')::date", s)
        s = re.sub(r"date\('now'\)", "CURRENT_DATE", s)
        s = re.sub(r"strftime\('%Y-%m',\s*(\w+(?:\.\w+)?)\)",
                   r"TO_CHAR(\1, 'YYYY-MM')", s)
        s = re.sub(r"strftime\('%m',\s*(\w+(?:\.\w+)?)\)",
                   r"TO_CHAR(\1, 'MM')", s)
        s = re.sub(r"strftime\('%Y',\s*(\w+(?:\.\w+)?)\)",
                   r"TO_CHAR(\1, 'YYYY')", s)
        s = re.sub(r"strftime\('%B',\s*(\w+(?:\.\w+)?)\)",
                   r"TO_CHAR(\1, 'Month')", s)
        s = re.sub(r"time\((\w+(?:\.\w+)?)\)",
                   r"\1::time without time zone", s)
        s = re.sub(r'\?', '%s', s)
        return s


class _PGCursor:
    def __init__(self, conn):
        import psycopg2
        import psycopg2.extras
        self._cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self._conn = conn

    def execute(self, sql, params=None):
        sql = _PGConnection._convert(sql)
        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)
        except Exception as e:
            if hasattr(e, 'diag') and hasattr(e.diag, 'sqlstate'):
                if e.diag.sqlstate == '23505':
                    raise IntegrityError(str(e))
            raise
        return self

    def executemany(self, sql, params_list):
        sql = _PGConnection._convert(sql)
        for params in params_list:
            self._cursor.execute(sql, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row:
            return _Row(row)
        return None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [_Row(r) for r in rows]

    @property
    def lastrowid(self):
        cur = self._conn.cursor()
        cur.execute("SELECT LASTVAL()")
        return cur.fetchone()[0]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class _Row:
    def __init__(self, row):
        self._row = row
        self._keys = list(row.keys()) if hasattr(row, 'keys') else []

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return self._row[self._keys[key]]
        return self._row[key]

    def __getattr__(self, name):
        if name in self._row:
            return self._row[name]
        raise AttributeError(name)

    def keys(self):
        return self._keys

    def __iter__(self):
        return iter(self._row.values())

    def __len__(self):
        return len(self._keys)

    def __contains__(self, key):
        return key in self._row

    def __repr__(self):
        return dict(self._row).__repr__()
