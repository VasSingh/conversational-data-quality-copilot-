import duckdb, os
p = os.path.join('data','dq_exceptions.csv')
print('path exists:', os.path.exists(p))
conn = duckdb.connect(':memory:')
conn.execute(f"CREATE TABLE dq_exceptions AS SELECT * FROM read_csv_auto('{p}')")
print('columns:', conn.execute("PRAGMA table_info('dq_exceptions')").fetchall())
print('count:', conn.execute('SELECT COUNT(*) FROM dq_exceptions').fetchone()[0])
print('min/max date:', conn.execute("SELECT MIN(exception_date), MAX(exception_date) FROM dq_exceptions").fetchall())
print('sample rows:', conn.execute("SELECT exception_date, rule_name FROM dq_exceptions ORDER BY exception_date DESC LIMIT 10").fetchall())
