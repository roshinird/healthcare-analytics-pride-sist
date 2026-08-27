-- 1. Number of patients by gender

SELECT
    Gender,
    COUNT(*) AS patient_count
FROM patients
GROUP BY Gender
ORDER BY patient_count DESC;
-- 1. Number of patients by gender

SELECT
    Gender,
    COUNT(*) AS patient_count
FROM patients
GROUP BY Gender
ORDER BY patient_count DESC;


-- 2. Number of patients by medical condition

SELECT
    "Medical Condition",
    COUNT(*) AS patient_count
FROM patients
GROUP BY "Medical Condition"
ORDER BY patient_count DESC;
-- 3. Average billing amount by medical condition

SELECT
    [Medical Condition],
    ROUND(AVG([Billing Amount]), 2) AS average_billing
FROM patients
GROUP BY [Medical Condition]
ORDER BY average_billing DESC;
-- 4. Number of patients by admission type

SELECT
    [Admission Type],
    COUNT(*) AS patient_count
FROM patients
GROUP BY [Admission Type]
ORDER BY patient_count DESC;
-- 5. Average billing amount by insurance provider

SELECT
    [Insurance Provider],
    ROUND(AVG([Billing Amount]), 2) AS average_billing
FROM patients
GROUP BY [Insurance Provider]
ORDER BY average_billing DESC;
-- 6. Number of patients by test result

SELECT
    [Test Results],
    COUNT(*) AS patient_count
FROM patients
GROUP BY [Test Results]
ORDER BY patient_count DESC;
-- 7. Average patient age by medical condition

SELECT
    [Medical Condition],
    ROUND(AVG(Age), 2) AS average_age
FROM patients
GROUP BY [Medical Condition]
ORDER BY average_age DESC;
-- 8. Number of patients by medication

SELECT
    Medication,
    COUNT(*) AS patient_count
FROM patients
GROUP BY Medication
ORDER BY patient_count DESC;
-- 9. Average hospital stay by admission type

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