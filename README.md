# Swan's Island Boat

Josh and Sarah's ferry app for the Bass Harbor – Swan's Island crossing. It lives at
**https://hectrvictorious.github.io/swans-island-boat/** and installs on a phone as its own app.

## What's in here

- `site/` — the app. `index.html` is the whole page (schedule engine, chart, planner, tickets, facts).
  `manifest.json`, `sw.js` and the icons make it installable and let it open with no signal.
  `conditions.json` holds the latest wind, seas, tides and New England 511 ferry notices.
  `photos/` — drop pictures here and list them in `photos/photos.json` as `{"src": "name.jpg", "caption": "..."}`; the Info tab shows them.
- `tools/fetch_conditions.py` — rebuilds `conditions.json` from the National Weather Service, NOAA tides and New England 511.
- `.github/workflows/site.yml` — publishes the site on every push and refreshes the conditions every 30 minutes.

## Keeping it current

- **Timetable:** the tables are at the top of the schedule engine in `site/index.html` (`SCHED`, `HOLIDAY`, `SEASONS`). When the state finalizes a summer schedule or changes the winter one, update the minutes-after-midnight values and the season dates, then push.
- **Fares:** the `FARES` list in the page script.
- **If GitHub emails that the scheduled workflow was disabled for inactivity** (it does that after 60 quiet days), open the Actions tab and enable it again.

Not affiliated with the Maine State Ferry Service. Confirm with the terminal before a trip that matters.
