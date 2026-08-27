import sqlite3
import pandas as pd

# Paths
csv_path = "backend/data/processed/healthcare_cleaned.csv"
db_path = "backend/data/database/healthcare.db"

# Load cleaned dataset
df = pd.read_csv(csv_path)

# Connect to SQLite database
connection = sqlite3.connect(db_path)

# Create healthcare table
df.to_sql("patients", connection, if_exists="replace", index=False)

# Check number of records
cursor = connection.cursor()
cursor.execute("SELECT COUNT(*) FROM patients")
count = cursor.fetchone()[0]

print("Database created successfully!")
print("Records inserted:", count)

connection.close()