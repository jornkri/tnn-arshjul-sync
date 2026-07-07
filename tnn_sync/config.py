from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class Config:
    group_id: str
    season: dict
    categories: dict
    activity_subgroups: dict   # {subgroup_id: category_key}
    training_subgroup_id: str
    fpn_weekdays: list[int]
    output_path: str

def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(
        group_id=data["group_id"],
        season=data["season"],
        categories=data["categories"],
        activity_subgroups=data["activity_subgroups"],
        training_subgroup_id=data["training_subgroup_id"],
        fpn_weekdays=data.get("fpn_weekdays", []),
        output_path=data.get("output_path", "public/arshjul.json"),
    )
