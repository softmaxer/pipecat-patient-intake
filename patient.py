from typing import List, Optional, TypedDict


class Prescription(TypedDict):
    medication: str
    dosage: str


class Allergy(TypedDict):
    name: str


class Condition(TypedDict):
    name: str


class Patient(TypedDict):
    name: str
    date_of_birth: str
    prescriptions: Optional[List[Prescription]]
    allergies: Optional[List[Allergy]]
    conditions: Optional[List[Condition]]
    visit_reasons: str
    visit_date: str


def summarize(patient: Patient) -> str:
    summary = ""
    summary += f"{patient['name']}'s visit for {patient['visit_reasons']}."
    if patient["prescriptions"]:
        summary += f"Patient is currently under {patient['prescriptions']}"
    if patient["allergies"]:
        summary += f" Patient has the following allergies:\n"
        summary += "\n".join([al["name"] for al in patient["allergies"]])
    if patient["conditions"]:
        summary += f"patient has a medical history with the follwing conditions: {patient['conditions']} "
    return summary
