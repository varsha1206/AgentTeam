"""
dataset_generator.py

Generates controlled evaluation datasets with known injected errors.
Returns GroundTruth for each dataset so detection accuracy can be computed.

Datasets are deterministic — same output every time.
No randomness. No side effects beyond writing files.
"""

from pathlib import Path

import pandas as pd

from agentteam.evaluation.structured_outputs import GroundTruth, InjectedError

DATASETS_DIR = Path(__file__).parent / "datasets"
CLEAN_DIR = DATASETS_DIR / "clean"
BROKEN_DIR = DATASETS_DIR / "broken"


# -----------------------------
# Base dataset
# -----------------------------


def generate_base_dataset(rows: int = 20) -> pd.DataFrame:
    """
    Generates a clean base dataset with no errors.
    Deterministic — same output every time.
    """
    names = [
        "Alice",
        "Bob",
        "Carol",
        "David",
        "Eve",
        "Frank",
        "Grace",
        "Henry",
        "Iris",
        "Jack",
        "Karen",
        "Leo",
        "Mona",
        "Nate",
        "Olivia",
        "Paul",
        "Quinn",
        "Rosa",
        "Sam",
        "Tina",
    ]
    departments = ["HR", "IT", "Finance", "Engineering", "Sales"]
    base_salary = 50000

    return pd.DataFrame(
        {
            "id": list(range(1, rows + 1)),
            "name": names[:rows],
            "age": [25 + i % 15 for i in range(rows)],
            "salary": [base_salary + (i * 1000) for i in range(rows)],
            "department": [departments[i % len(departments)] for i in range(rows)],
        }
    )


# -----------------------------
# Injectors
# -----------------------------


def inject_type_mismatches(df: pd.DataFrame) -> list[InjectedError]:
    """
    Injects string values into numeric columns.
    Modifies df in place. Returns list of InjectedError.
    """
    errors = []

    df["age"] = df["age"].astype(object)
    df["salary"] = df["salary"].astype(object)

    df.at[2, "age"] = "twenty"
    errors.append(InjectedError(row=2, column="age", error_type="type_mismatch"))

    df.at[7, "age"] = "abc"
    errors.append(InjectedError(row=7, column="age", error_type="type_mismatch"))

    df.at[11, "salary"] = -999
    errors.append(InjectedError(row=11, column="salary", error_type="range_violation"))

    return errors


def inject_missing_values(df: pd.DataFrame) -> list[InjectedError]:
    """
    Injects None into non-nullable columns.
    Modifies df in place. Returns list of InjectedError.
    """
    errors = []

    df.at[4, "name"] = None
    errors.append(InjectedError(row=4, column="name", error_type="missing_value"))

    df.at[9, "salary"] = None
    errors.append(InjectedError(row=9, column="salary", error_type="missing_value"))

    df.at[14, "department"] = None
    errors.append(
        InjectedError(row=14, column="department", error_type="missing_value")
    )

    return errors


def inject_range_violations(df: pd.DataFrame) -> list[InjectedError]:
    """
    Injects out-of-range values into numeric columns.
    Modifies df in place. Returns list of InjectedError.
    """
    errors = []

    df.at[1, "age"] = 200
    errors.append(InjectedError(row=1, column="age", error_type="range_violation"))

    df.at[6, "salary"] = -50000
    errors.append(InjectedError(row=6, column="salary", error_type="range_violation"))

    return errors


def inject_duplicates(df: pd.DataFrame) -> list[InjectedError]:
    """
    Duplicates an existing row.
    Modifies df in place. Returns list of InjectedError.
    """
    errors = []
    duplicate_row = df.iloc[0].copy()
    df.iloc[3] = duplicate_row
    errors.append(InjectedError(row=3, column="id", error_type="duplicate"))
    return errors


# -----------------------------
# Save
# -----------------------------


def save_dataset(df: pd.DataFrame, output_path: Path) -> None:
    """Write dataset to CSV. Creates parent directories if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")


# -----------------------------
# Named datasets
# -----------------------------


def generate_clean_dataset(rows: int = 20) -> GroundTruth:
    """
    Clean dataset with no injected errors.
    Expected quarantine: 0 rows.
    """
    filename = "eval_clean.csv"
    output_path = CLEAN_DIR / filename
    df = generate_base_dataset(rows)
    save_dataset(df, output_path)

    return GroundTruth(
        dataset_name="clean",
        filename=filename,
        total_rows=len(df),
        injected_errors=[],
        expected_quarantine_rows=0,
    )


def generate_dataset_1(rows: int = 20) -> GroundTruth:
    """
    Dataset 1 — Type mismatches and range violations.

    Injected errors:
        row 2,  age    = "twenty"   (type_mismatch)
        row 7,  age    = "abc"      (type_mismatch)
        row 11, salary = -999       (range_violation)

    Expected quarantine: 3 rows.
    """
    filename = "eval_dataset_1.csv"
    output_path = BROKEN_DIR / filename
    df = generate_base_dataset(rows)
    errors = inject_type_mismatches(df)
    save_dataset(df, output_path)

    return GroundTruth(
        dataset_name="dataset_1_type_mismatches",
        filename=filename,
        total_rows=len(df),
        injected_errors=errors,
        expected_quarantine_rows=len(errors),
    )


def generate_dataset_2(rows: int = 20) -> GroundTruth:
    """
    Dataset 2 — Missing values in non-nullable columns.

    Injected errors:
        row 4,  name       = None   (missing_value)
        row 9,  salary     = None   (missing_value)
        row 14, department = None   (missing_value)

    Expected quarantine: 3 rows.
    """
    filename = "eval_dataset_2.csv"
    output_path = BROKEN_DIR / filename
    df = generate_base_dataset(rows)
    errors = inject_missing_values(df)
    save_dataset(df, output_path)

    return GroundTruth(
        dataset_name="dataset_2_missing_values",
        filename=filename,
        total_rows=len(df),
        injected_errors=errors,
        expected_quarantine_rows=len(errors),
    )


def generate_dataset_3(rows: int = 20) -> GroundTruth:
    """
    Dataset 3 — Mixed errors (type mismatch + missing value + range violation).

    Injected errors:
        row 2,  age    = "twenty"   (type_mismatch)
        row 4,  name   = None       (missing_value)
        row 6,  salary = -50000     (range_violation)

    Note: script crash injection is handled by the experiment runner,
    not by this generator. Dataset 3 is the data-level broken case.
    The experiment runner optionally injects a script failure on top.

    Expected quarantine: 3 rows.
    """
    filename = "eval_dataset_3.csv"
    output_path = BROKEN_DIR / filename
    df = generate_base_dataset(rows)

    df["age"] = df["age"].astype(object)
    df["salary"] = df["salary"].astype(object)

    errors = []

    df.at[2, "age"] = "twenty"
    errors.append(InjectedError(row=2, column="age", error_type="type_mismatch"))

    df.at[4, "name"] = None
    errors.append(InjectedError(row=4, column="name", error_type="missing_value"))

    df.at[6, "salary"] = -50000
    errors.append(InjectedError(row=6, column="salary", error_type="range_violation"))

    save_dataset(df, output_path)

    return GroundTruth(
        dataset_name="dataset_3_mixed_errors",
        filename=filename,
        total_rows=len(df),
        injected_errors=errors,
        expected_quarantine_rows=len(errors),
    )


import random


def generate_base_dataset_at_scale(rows: int) -> pd.DataFrame:
    """
    Deterministic large dataset generator. Does not depend on the fixed
    20-name list used by the small controlled datasets.
    """
    departments = ["HR", "IT", "Finance", "Engineering", "Sales"]
    return pd.DataFrame(
        {
            "id": list(range(1, rows + 1)),
            "name": [f"Employee_{i}" for i in range(1, rows + 1)],
            "age": [20 + (i % 45) for i in range(rows)],
            "salary": [40000 + (i * 137) % 60000 for i in range(rows)],
            "department": [departments[i % len(departments)] for i in range(rows)],
        }
    )


def inject_proportional_errors(
    df: pd.DataFrame, error_rate: float = 0.05, seed: int = 42
) -> list[InjectedError]:
    """
    Injects errors into a fixed proportion of rows, cycling through
    type_mismatch, missing_value, and range_violation. Deterministic
    via a fixed seed — same output on every generation run.
    """
    rng = random.Random(seed)
    n_errors = int(len(df) * error_rate)
    rows = rng.sample(range(len(df)), n_errors)

    df["age"] = df["age"].astype(object)
    df["salary"] = df["salary"].astype(object)

    error_cycle = ["type_mismatch", "missing_value", "range_violation"]
    errors = []

    for idx, row in enumerate(rows):
        kind = error_cycle[idx % len(error_cycle)]
        if kind == "type_mismatch":
            df.at[row, "age"] = "invalid"
            errors.append(InjectedError(row=row, column="age", error_type=kind))
        elif kind == "missing_value":
            df.at[row, "salary"] = None
            errors.append(InjectedError(row=row, column="salary", error_type=kind))
        else:
            df.at[row, "salary"] = -1
            errors.append(InjectedError(row=row, column="salary", error_type=kind))

    return errors


def generate_scalability_dataset(
    rows: int = 1000, error_rate: float = 0.05
) -> GroundTruth:
    """
    Large dataset for scalability evaluation. Single variant, mixed
    error types, proportional rather than fixed error count.
    """
    filename = "eval_scalability.csv"
    output_path = BROKEN_DIR / filename
    df = generate_base_dataset_at_scale(rows)
    errors = inject_proportional_errors(df, error_rate=error_rate)
    save_dataset(df, output_path)

    return GroundTruth(
        dataset_name="scalability",
        filename=filename,
        dataset_category="scalability",
        total_rows=len(df),
        injected_errors=errors,
        expected_quarantine_rows=len(errors),
    )


# -----------------------------
# Generate all datasets at once
# -----------------------------


def generate_all() -> dict[str, GroundTruth]:
    """
    Generate all evaluation datasets and return their ground truths.
    Call this once before running experiments.
    """
    return {
        "clean": generate_clean_dataset(),
        "dataset_1": generate_dataset_1(),
        "dataset_2": generate_dataset_2(),
        "dataset_3": generate_dataset_3(),
        "scalability": generate_scalability_dataset(),
    }


if __name__ == "__main__":
    ground_truths = generate_all()
    for name, gt in ground_truths.items():
        print(
            f"{name}: {gt.total_rows} rows, {len(gt.injected_errors)} errors, "
            f"expected quarantine: {gt.expected_quarantine_rows}"
        )
