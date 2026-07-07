from tnn_sync.config import load_config, Config

YAML = """
group_id: "GROUP123"
season:
  year: 2026
  label: "TNN 2016-A"
  accent: "#E8112D"
categories:
  cup: {label: "Cup / turnering", color: "#FF4D4D", icon: "cup"}
category_rules:
  - ["cup", "cup"]
  - ["sosial", "sosialt"]
fallback_category: "sosialt"
ignore_activity_titles: ["tnn16-a", "tnn 16-a"]
output_path: "public/arshjul.json"
"""

def test_load_config(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(YAML, encoding="utf-8")
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.group_id == "GROUP123"
    assert cfg.season["year"] == 2026
    assert cfg.category_rules == [["cup", "cup"], ["sosial", "sosialt"]]
    assert cfg.fallback_category == "sosialt"
    assert cfg.ignore_activity_titles == ["tnn16-a", "tnn 16-a"]
    assert cfg.categories["cup"]["icon"] == "cup"
    assert cfg.output_path == "public/arshjul.json"

def test_load_config_defaults_optional_lists(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("""
group_id: "GROUP123"
season: {year: 2026, label: "TNN 2016-A", accent: "#E8112D"}
categories:
  cup: {label: "Cup / turnering", color: "#FF4D4D", icon: "cup"}
fallback_category: "sosialt"
""", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.category_rules == []
    assert cfg.fallback_category == "sosialt"
    assert cfg.ignore_activity_titles == []
