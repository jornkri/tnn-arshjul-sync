from tnn_sync.config import load_config, Config

YAML = """
group_id: "GROUP123"
season:
  year: 2026
  label: "TNN 2016-A"
  accent: "#E8112D"
categories:
  cup: {label: "Cup / turnering", color: "#FF4D4D", icon: "cup"}
activity_subgroups:
  SUBcup: cup
training_subgroup_id: "SUBtrening"
fpn_weekdays: [4]
output_path: "public/arshjul.json"
"""

def test_load_config(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(YAML, encoding="utf-8")
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.group_id == "GROUP123"
    assert cfg.season["year"] == 2026
    assert cfg.activity_subgroups == {"SUBcup": "cup"}
    assert cfg.training_subgroup_id == "SUBtrening"
    assert cfg.fpn_weekdays == [4]
    assert cfg.categories["cup"]["icon"] == "cup"
    assert cfg.output_path == "public/arshjul.json"
