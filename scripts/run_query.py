import duckdb, os
p = os.path.join('data','dq_exceptions.csv')
conn = duckdb.connect(':memory:')
conn.execute(f"CREATE TABLE dq_exceptions AS SELECT * FROM read_csv_auto('{p}')")
sql = "SELECT date_trunc('month', exception_date) AS month, COUNT(*) AS exceptions FROM dq_exceptions WHERE exception_date >= current_date - INTERVAL '6 months' GROUP BY month ORDER BY month"
print('running SQL:', sql)
try:
    rows = conn.execute(sql).fetchall()
    print('rows:', rows)
    df = conn.execute(sql).df()
    print('df cols:', df.columns.tolist(), 'shape:', df.shape)
except Exception as e:
    print('error:', e)
