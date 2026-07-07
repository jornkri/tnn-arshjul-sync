from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config:
    group_id: str
    season: dict
    categories: dict
    category_rules: list[list[str]]   # [[keyword, category], ...]
    fallback_category: str
    ignore_activity_titles: list[str]
    output_path: str

def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(
        group_id=data["group_id"],
        season=data["season"],
        categories=data["categories"],
        category_rules=data.get("category_rules", []),
        fallback_category=data["fallback_category"],
        ignore_activity_titles=data.get("ignore_activity_titles", []),
        output_path=data.get("output_path", "public/arshjul.json"),
    )
