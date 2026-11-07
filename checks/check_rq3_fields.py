"""RQ3 field check (design §10): frozen masks unchanged; every montage has an Ernie row; every row has both mask
fields or a note saying why not; no computed field is zero, negative or NaN.
CLI: python -m checks.check_rq3_fields
"""
import csv
import hashlib
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ROOT / "rq3_stimulation" / "simnibs" / "fields.csv"
MASKS = ("memory.nii.gz", "control_md.nii.gz")


def validate(montage_ids, rows, frozen, mask_bytes):
    errors = []
    for name in MASKS:
        if hashlib.sha256(mask_bytes[name]).hexdigest() != frozen.get(name):
            errors.append(f"{name} does not match FROZEN.sha256")
    ernie = {r["montage_id"] for r in rows if r["head_model"] == "ernie"}
    if montage_ids - ernie:
        errors.append(f"montages without an Ernie row: {sorted(montage_ids - ernie)}")
    for r in rows:
        values = [r["field_map"], r["field_control"]]
        if all(v == "" for v in values):
            if not r["note"]:
                errors.append(f"{r['montage_id']} ({r['head_model']}): no field and no note")
            continue
        try:
            nums = [float(v) for v in values]
        except ValueError:
            errors.append(f"{r['montage_id']} ({r['head_model']}): field missing for one mask")
            continue
        if any(math.isnan(v) or v <= 0 for v in nums):
            errors.append(f"{r['montage_id']} ({r['head_model']}): zero, negative or NaN field {nums}")
    return errors


def main():
    montage_ids = {r["montage_id"] for r in csv.DictReader((ROOT / "rq3_stimulation" / "montages.csv").open())}
    rows = list(csv.DictReader(FIELDS.open()))
    frozen = dict(line.split()[::-1] for line in (ROOT / "masks" / "FROZEN.sha256").read_text().splitlines() if line.strip())
    errors = validate(montage_ids, rows, frozen, {n: (ROOT / "masks" / n).read_bytes() for n in MASKS})
    for e in errors:
        print("FAIL:", e)
    done = sum(1 for r in rows if r["head_model"] == "ernie" and r["field_map"])
    print(f"{done} of {len(montage_ids)} montages have Ernie fields")
    if errors:
        sys.exit(1)
    print("RQ3 field check OK")


if __name__ == "__main__":
    main()
