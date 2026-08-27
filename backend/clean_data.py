import pandas as pd

# Load raw dataset
input_path = "backend/data/raw/healthcare_dataset.csv"
output_path = "backend/data/processed/healthcare_cleaned.csv"

df = pd.read_csv(input_path)

print("Original rows:", len(df))

# Remove duplicate rows
df = df.drop_duplicates()

print("Rows after removing duplicates:", len(df))

# Save cleaned dataset
df.to_csv(output_path, index=False)

print("Cleaned dataset saved successfully!")
print(output_path)