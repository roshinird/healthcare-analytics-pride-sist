import pandas as pd
import numpy as np

# Load cleaned dataset
file_path = "backend/data/processed/healthcare_cleaned.csv"
df = pd.read_csv(file_path)

print("Dataset loaded successfully!")
print("Rows:", len(df))
print("Columns:", len(df.columns))

# Create age groups using NumPy
conditions = [
    df["Age"] < 18,
    (df["Age"] >= 18) & (df["Age"] < 40),
    (df["Age"] >= 40) & (df["Age"] < 60),
    df["Age"] >= 60
]

categories = [
    "Child",
    "Young Adult",
    "Middle Aged",
    "Senior"
]

df["Age Group"] = np.select(
    conditions,
    categories,
    default="Unknown"
)

print("\nAge group counts:")
print(df["Age Group"].value_counts())
# Calculate billing statistics

average_billing = df["Billing Amount"].mean()
median_billing = df["Billing Amount"].median()
minimum_billing = df["Billing Amount"].min()
maximum_billing = df["Billing Amount"].max()

print("\nBilling Statistics:")
print("Average billing:", round(average_billing, 2))
print("Median billing:", round(median_billing, 2))
print("Minimum billing:", round(minimum_billing, 2))
print("Maximum billing:", round(maximum_billing, 2))
# Identify negative billing amounts

negative_billing = df[df["Billing Amount"] < 0]

print("\nNegative billing records:", len(negative_billing))
# Convert admission and discharge dates to datetime

df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
df["Discharge Date"] = pd.to_datetime(df["Discharge Date"])

# Calculate hospital stay duration

df["Stay Days"] = (
    df["Discharge Date"] - df["Date of Admission"]
).dt.days

print("\nHospital stay statistics:")
print("Average stay:", round(df["Stay Days"].mean(), 2), "days")
print("Minimum stay:", df["Stay Days"].min(), "days")
print("Maximum stay:", df["Stay Days"].max(), "days")
# Create medical condition summary

condition_summary = df.groupby("Medical Condition").agg(
    Patient_Count=("Name", "count"),
    Average_Age=("Age", "mean"),
    Average_Billing=("Billing Amount", "mean"),
    Average_Stay_Days=("Stay Days", "mean")
).round(2)

print("\nMedical Condition Summary:")
print(condition_summary)
# Save transformed dataset

output_path = "backend/data/processed/healthcare_transformed.csv"

df.to_csv(output_path, index=False)

print("\nTransformed dataset saved successfully!")
print("File:", output_path)
