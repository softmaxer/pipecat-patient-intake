import pytest

from patient import Patient, summarize


sample_patient: Patient = {
    "name": "John Doe",
    "date_of_birth": "1999-12-03",
    "visit_reasons": "back ache",
    "visit_date": "2024-12-22",
    "conditions": None,
    "allergies": None,
    "prescriptions": None,
}


sample_patient_with_allergies: Patient = {
    "name": "John Doe",
    "date_of_birth": "1999-12-03",
    "visit_reasons": "back ache",
    "visit_date": "2024-12-22",
    "conditions": None,
    "allergies": [{"name": "peanut allergy"}],
    "prescriptions": None,
}


def test_basic_summary():
    assert summarize(sample_patient) == "John Doe's visit for back ache."


def test_summary_with_allergies():
    assert (
        summarize(sample_patient_with_allergies)
        == "John Doe's visit for back ache. Patient has the following allergies:\npeanut allergy"
    )
