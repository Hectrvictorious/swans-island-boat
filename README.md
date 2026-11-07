# Swan's Island Boat

Josh and Sarah's ferry app for the Bass Harbor – Swan's Island crossing. It lives at
**https://hectrvictorious.github.io/swans-island-boat/** and installs on a phone as its own app.

## What's in here

- `site/` — the app. `index.html` is the whole page (schedule engine, chart, planner, tickets, facts).
  `manifest.json`, `sw.js` and the icons make it installable and let it open with no signal.
  `conditions.json` holds the latest wind, gusts, seas, tides and New England 511 ferry notices.
  `data/sync.json` is the archive of shared messages (planned trips, reservation counts, boat of the day). Every entry is encrypted; see below.
  `photos/` — drop pictures here and list them in `photos/photos.json` as `{"src": "name.jpg", "caption": "..."}`; the Info tab shows them.
- `tools/fetch_conditions.py` — rebuilds `conditions.json` from the National Weather Service (marine forecast, alerts, hourly forecast, and the raw forecast grid for hour-by-hour gusts), NOAA tides and New England 511.
- `tools/merge_sync.py` — copies the encrypted messages from the relay into `site/data/sync.json`.
- `.github/workflows/site.yml` — publishes the site on every push; every 30 minutes it refreshes the conditions and archives the shared messages.

## Updates reach the phones by themselves

Push to `main` and the workflow publishes. The next time either phone opens the app (or brings it back to the screen), the service worker picks up the new build and the page refreshes once. Nobody reinstalls anything. A short "New in the boat app" note appears once when `APP_VERSION` in the page changes.

## Shared trips, reservations and the boat of the day

- Tap a boat on the Plan tab (or the Now tab) to plan a trip: who's going, car or walking on, who holds the car reservation, whose phone has the tickets, the boat back, a note.
- Phones send these through a public relay (ntfy.sh, topic in the workflow) as AES-GCM sealed messages. The family key is only on the phones: it rides in the family link after `#join=`, and the part of a link after `#` never reaches any server. The relay, GitHub and anyone reading this repo see only ciphertext.
- The relay keeps messages about 12 hours, so the workflow archives them in `site/data/sync.json` (trips for 400 days, ride counts for 3 years, reservation posts and package lists for 3 weeks, the last few boat and problem notes). GitHub runs that schedule only every few hours in practice, so phones re-send any message the archive is still missing after 3 hours.
- To link a phone: open the family link on it, or on a linked phone go to Info → "Send … the link".
- Optional buzz: each person has an ntfy topic shown on the Info tab; subscribe in the ntfy app to get a notification when the other one plans a trip.
- To start over with a new key: generate 32 random bytes (base64url), send new links, and change `SYNC_FP` in the workflow to the first 8 hex digits of the key's SHA-256. Old messages become unreadable.

## The daily Facebook check

The car reservation counts come from the daily "Traffic" post in the island's Facebook group. A Claude scheduled task on Josh's computer opens the group in Claude's browser (signed in to Facebook there), copies the newest Traffic post, opens this app in the same browser and calls `window.boatAPI.importTraffic(text, 'facebook', url)`. In the morning it also reads the Henry Lee's and the Philbrook's VesselFinder pages and calls `window.boatAPI.boatReport(...)`. If something goes wrong it calls `window.boatAPI.reportProblem(reason)`, and the phones show a red "Couldn't reach reservations" box with the reason, a call button, and a paste-the-post fallback.

Each run it also reads the newest "FedEx/UPS at TIMS" post in the HOPKINS FREIGHT group (The Island Market & Supply's daily list of packages waiting) and calls `window.boatAPI.importPackages(posts)`. The app matches Josh's and Sarah's whole names ("(2) Sarah Greene"), not a lone first name, so lines like "Joshua Sarah …" or "(3+1 for Josh) …" don't count. Only their lines are shared; nobody else's name leaves that browser. When the newest list has a package for either of them, a big banner tops the Now tab on both phones until someone taps Got it.

`window.boatAPI.state()` reports whether that browser is linked, what it already has, and what the run should do (`todo`: `traffic`, `boat`, `packages`).

## Mainesota Grill

The Now tab has a card for the Mainesota Grill food trailer (737 Atlantic Road): Order online (their own order-ahead page, which can't be shown inside another page, so it opens on top of the app), their Facebook page for hours and the day's menu, and directions.

## Keeping it current

- **Timetable:** the tables are at the top of the schedule engine in `site/index.html` (`SCHED`, `HOLIDAY`, `SEASONS`). When the state finalizes a summer schedule or changes the winter one, update the minutes-after-midnight values and the season dates, then push.
- **Fares:** the `FARES` list in the page script.
- **If GitHub emails that the scheduled workflow was disabled for inactivity** (it does that after 60 quiet days), open the Actions tab and enable it again.

Not affiliated with the Maine State Ferry Service. Confirm with the terminal before a trip that matters.
