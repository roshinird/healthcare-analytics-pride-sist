import sqlite3
DATABASE_PATH = "backend/data/database/healthcare.db"


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def get_patient_count():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM patients")

    count = cursor.fetchone()[0]

    connection.close()

    return count


def get_patient_count_by_condition():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            [Medical Condition],
            COUNT(*) AS patient_count
        FROM patients
        GROUP BY [Medical Condition]
        ORDER BY patient_count DESC
    """)

    results = cursor.fetchall()

    connection.close()

    return results


def get_billing_summary():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            ROUND(AVG([Billing Amount]), 2),
            ROUND(MIN([Billing Amount]), 2),
            ROUND(MAX([Billing Amount]), 2)
        FROM patients
    """)

    result = cursor.fetchone()

    connection.close()

    return result