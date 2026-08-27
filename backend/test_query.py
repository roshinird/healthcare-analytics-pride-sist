import sqlite3

connection = sqlite3.connect("backend/data/database/healthcare.db")
cursor = connection.cursor()

query = """
SELECT
    [Admission Type],
    ROUND(
        AVG(
            julianday([Discharge Date]) -
            julianday([Date of Admission])
        ),
        2
    ) AS average_stay_days
FROM patients
GROUP BY [Admission Type]
ORDER BY average_stay_days DESC;
"""

cursor.execute(query)

for row in cursor.fetchall():
    print(row)

connection.close()