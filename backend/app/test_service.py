from app.services.patient_service import get_patient_count
from app.services.patient_service import get_patient_count_by_condition
from app.services.patient_service import get_billing_summary

count = get_patient_count()

print("Total patients:", count)

condition_results = get_patient_count_by_condition()

print("\nPatients by medical condition:")

for row in condition_results:
    print(row)

billing = get_billing_summary()

print("\nBilling summary:")
print("Average:", billing[0])
print("Minimum:", billing[1])
print("Maximum:", billing[2])