# src/agentteam/utils/test_data_generator.py

"""Generates controlled broken test datasets for pipeline evaluation."""

from pathlib import Path

import pandas as pd


def generate_broken_csv(output_path: Path) -> None:
    """
    Generates a CSV with controlled errors for repair agent testing.
    Known injected errors:
      - Row 2: age is 'abc' (type mismatch)
      - Row 3: name is null (missing non-nullable)
      - Row 4: salary is -999 (out of range)
      - Row 5: duplicate of row 1
      - Row 6: all critical fields null (should quarantine)
    """
    data = {
        "id": [1, 2, 3, 4, 1, 6],
        "name": ["Alice", "Bob", None, "Diana", "Alice", "Eve"],
        "age": [30, "abc", 25, 28, 30, None],
        "salary": [50000, 60000, 70000, -999, 50000, None],
        "department": ["Eng", "HR", "Eng", "Sales", "Eng", None],
    }
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Generated broken CSV: {output_path} — {len(df)} rows, 5 known errors")


if __name__ == "__main__":
    path = Path("workspace/input/broken_employee_data.csv")
    generate_broken_csv(path)
