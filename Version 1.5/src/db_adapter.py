import os
import re
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL', '')
USING_PG = 'postgres' in DATABASE_URL

class IntegrityError(Exception):
    pass


def get_connection():
    if 'postgres' in DATABASE_URL:
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
        self._conn.autocommit = False

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
        if self._conn:
            self._conn.commit()

    def rollback(self):
        if self._conn:
            self._conn.rollback()

    def close(self):
        self._conn.close()

    @staticmethod
    def _convert(sql):
        s = sql.strip()
        if s.upper().startswith('PRAGMA'):
            return 'SELECT 1'
        s = re.sub(r"(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b",
                    "INSERT INTO", s)
        if 'OR IGNORE' in sql.upper():
            s += " ON CONFLICT DO NOTHING"
        s = re.sub(r"(?i)\bINSERT\s+OR\s+REPLACE\s+INTO\b",
                    "INSERT INTO", s)
        if 'OR REPLACE' in sql.upper():
            s += " ON CONFLICT DO NOTHING"
        s = re.sub(r"(?i)\bBEGIN\s+IMMEDIATE\b",
                    "BEGIN", s)
        s = re.sub(r"datetime\('now',\s*'([-+])\s*'\s*\|\|\s*\?\s*\|\|\s*'(\w+)'\s*\)",
                   r"CURRENT_TIMESTAMP \1 INTERVAL '1 \2' * %s", s)
        s = re.sub(r"datetime\('now'(?:,\s*'([^']+)')?\)",
                   r"CURRENT_TIMESTAMP", s)
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
        self._last_insert_id = None

    def execute(self, sql, params=None):
        sql = _PGConnection._convert(sql)
        is_insert = sql.strip().upper().startswith('INSERT') and 'RETURNING' not in sql.upper()
        if is_insert:
            sql += " RETURNING id"
        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)
            if is_insert:
                row = self._cursor.fetchone()
                self._last_insert_id = row['id'] if row else None
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
        if self._last_insert_id is not None:
            return self._last_insert_id
        # Fallback: query last sequence value (not concurrent-safe, but rare)
        cur = self._conn.cursor()
        cur.execute("SELECT LASTVAL()")
        val = cur.fetchone()[0]
        cur.close()
        return val

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
