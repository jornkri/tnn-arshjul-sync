import json
from pathlib import Path
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"

def load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

def validate_plan(plan: dict) -> None:
    Draft202012Validator(load_schema()).validate(plan)
