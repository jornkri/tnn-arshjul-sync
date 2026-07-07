# TNN Årshjul — Sync backend

Fetches the season plan from Spond and publishes `public/arshjul.json` to GitHub
Pages every 15 minutes. The iOS app reads that JSON. See
`docs/superpowers/plans/2026-07-07-tnn-arshjul-sync.md` and the design spec in the
app repo.

## One-time setup

1. **Install:** `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
2. **Discover ids / inspect events:**
   ```bash
   SPOND_USERNAME='you@example.com' SPOND_PASSWORD='...' python scripts/dump_groups.py
   # inspect a group's events (to design category rules):
   SPOND_USERNAME='...' SPOND_PASSWORD='...' python scripts/dump_events.py <group_id>
   ```
3. **Configure:** `cp config.example.yaml config.yaml`, set `group_id`, `season`,
   the 6 `categories`, the `category_rules` (title keyword → category, first match
   wins), `fallback_category`, and `ignore_activity_titles` (one-off titles to drop).
   Recurring events (those with a Spond `seriesId`) become the weekly training
   pattern automatically; one-off events become categorized activities. Commit the
   config (ids are not secret): `git add -f config.yaml && git commit -m "chore: real Spond config"`.
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
