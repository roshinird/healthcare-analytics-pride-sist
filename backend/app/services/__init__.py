"""Service layer.

Dev B owns `queries.py` (SQL), `analytics.py` (Pandas), `stats.py` (NumPy) and
`report.py` (Matplotlib). Dev A owns only `datasource.py` and `dev_fixtures.py`,
which resolve *which* implementation serves a request and provide contract-shaped
fixtures while Dev B's layer is absent.
"""
