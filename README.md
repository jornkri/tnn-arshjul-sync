# TNN Årshjul — Sync backend

Fetches the season plan from Spond and publishes `public/arshjul.json` to GitHub
Pages every 15 minutes. The iOS app reads that JSON. See
`docs/superpowers/plans/2026-07-07-tnn-arshjul-sync.md` and the design spec in the
app repo.

## One-time setup

1. **Install:** `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
2. **Discover Spond ids:**
   ```bash
   SPOND_USERNAME='you@example.com' SPOND_PASSWORD='...' python scripts/dump_groups.py
   ```
3. **Configure:** `cp config.example.yaml config.yaml`, fill in `group_id`,
   `activity_subgroups` (subgroup id → category), `training_subgroup_id`,
   `fpn_weekdays`, and `season`. Commit it (ids are not secret):
   `git add -f config.yaml && git commit -m "chore: real Spond config"`.
4. **GitHub secrets:** in repo Settings → Secrets and variables → Actions, add
   `SPOND_USERNAME` and `SPOND_PASSWORD` (a Spond account that is a member of the group).
5. **Enable Pages:** Settings → Pages → Source = "GitHub Actions".

## Local run

```bash
SPOND_USERNAME='...' SPOND_PASSWORD='...' python -m tnn_sync.main
cat public/arshjul.json
```

## Tests

```bash
pytest -q
```
