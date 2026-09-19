# PharmMS — Pharmacy Management System v2.0.0

**Designed & Developed by Jayant**

Pharmaceutical store inventory management and drug reference software: a Flask
API, a React interface, a sealed reference database, and a single-file Windows
executable.

---

## Quick start
### Install the desktop app (recommended)

```powershell
cd backend
.\build_exe.ps1          # produce dist\PharmMS.exe
.\install_app.ps1        # install + create shortcuts
```

This installs to `%LOCALAPPDATA%\Programs\PharmMS` — **no administrator rights
needed** — and creates a shortcut on your Desktop and in the Start Menu.

```powershell
.\install_app.ps1 -Uninstall              # remove app + shortcuts, keep data
.\install_app.ps1 -Uninstall -KeepData    # same, and skip the data prompt
```

### Running it
Double-click **PharmMS** on your Desktop. It opens in its **own application
window** (via the Windows WebView2 runtime) — no browser tab, no console window,
no internet connection.

Closing the window quits the app completely; nothing lingers in the background.

### Build the executable yourself

```powershell
cd backend
.\build_exe.ps1
```

This builds the React frontend, then freezes everything into
`backend\dist\PharmMS.exe` (~14 MB). Options:

| Flag | Effect |
|---|---|
| `-SkipFrontend` | Reuse the existing `frontend/build` (much faster) |
| `-Clean` | Delete previous build artefacts first |

### Run in development

```powershell
# Terminal 1 — API on :5000
cd backend
.\venv\Scripts\python.exe run.py

# Terminal 2 — React dev server on :3000 (hot reload)
cd frontend
npm start
```

The frontend auto-detects the port: on `:3000` it calls the API on `:5000`;
otherwise it uses same-origin `/api`, which is how the packaged build works.

---

## What changed in v2.0
### It is now a desktop app
Previously the executable started a server and opened a browser tab, with a
console window behind it. It now runs as a proper Windows application:

- **Native window** titled *Pharmacy Management System*, rendered by the WebView2
  engine (the same Chromium core as Edge). No browser, no address bar.
- **No console window.** The build is `windowed`; the only window is the app.
- **Its own icon** on the Desktop, Start Menu and taskbar.
- **Port fallback.** If something already holds port 5000 the app picks a free
  port instead of refusing to start.
- **Graceful degradation.** If no GUI backend is available the app falls back to
  the system browser rather than failing, so it still opens on a locked-down
  machine.

**Your records live outside the install folder** at
`%LOCALAPPDATA%\PharmMS\pharmacy.db`. Uninstalling, reinstalling or upgrading the
app never touches your data — the installer asks before deleting records, and
`-KeepData` skips the question entirely.

### New in this revision
**Local data storage with backups.** A *Data & backups* page shows exactly where
`pharmacy.db` lives, and offers snapshot, export, import and restore. A snapshot
is taken automatically on every startup and the last 10 are kept, so an
accidental delete or a bad edit can be rolled back. Snapshots use SQLite's
online backup API rather than a file copy, which is safe while the app is
running.

**Alternative medicine finder.** A new *Alternatives* page answers two
questions: "what else treats the same thing as this medicine?" (ranked by
indicating-text overlap, drug class, route and form) and "show me everything
stocked for this condition", grouped by therapeutic class. Selecting a patient
screens every result for allergies and contraindications and sorts blocked
options to the bottom rather than hiding them. Prices and stock are shown
side by side so the comparison is actionable.

**Fully offline.** Verified: the built bundle contains no external URLs at all —
no CDN fonts, no analytics, no telemetry. The database lives in
`%LOCALAPPDATA%\PharmMS`, so it survives the executable being moved or replaced.
The API binds to `127.0.0.1` only.

**More medicines.** The reference set grew from 27 to 40, adding sulfonylureas,
DPP-4 inhibitors, basal insulin, ARBs, beta blockers, newer statins,
anticoagulants, antiplatelets, tetracyclines, cephalosporins, antifungals,
antivirals and artemisinin combination therapy — with 69 dosage guides.

**Catalogue importer.** `import_medicines.py` loads a CSV or JSON catalogue
(CDSCO, Jan Aushadhi, NPPA price lists, or your own supplier sheet) with
flexible column-name mapping. See *Expanding the catalogue* below.

### Bugs fixed

These were real defects, not refactors:

1. **`/api/inventory/alerts` was completely dead.** `InventoryOptimizer.get_stock_alerts()`
   imported `Inventory` twice inside one function body, which makes Python treat
   the name as local and raise `UnboundLocalError` on first use. Every stock
   alert — and therefore the dashboard's low-stock and expiry counters — silently
   returned nothing.
2. **Contraindication checking never fired.** `check_contraindications(medicine_id, patient_id)`
   was being called with the arguments reversed, so it compared the wrong two
   records and reported "no contraindications" for every patient.
3. **The dosage calculator always reported "no interactions".** It called
   `checkInteractions(medicineId, '')` with an empty medication list instead of
   the patient's own `current_medications`.
4. **Drug cycle lengths were negative.** `standard_cycle` was written as `5-7`,
   which Python evaluates as `5 - 7 == -2`. Now returned as the string `"5-7"`.
5. **Penicillin allergy did not flag Amoxicillin.** Matching was a naive
   substring test, so a recorded penicillin allergy was ignored for every other
   beta-lactam. There is now a documented cross-reactivity map.
6. **The Patients and Prescriptions panels were placeholders.** Both are now
   fully implemented.
7. **`/static/*` assets 404'd in the packaged build.** Flask's built-in static
   route shadowed the React bundle. The app factory is now created with
   `static_folder=None` and serves the bundle explicitly.
8. **Reset-seeding destroyed user data.** The old `init_db.py` called
   `db.drop_all()` unconditionally. Seeding is now idempotent and additive, and
   dropping data requires the explicit `--reset` flag.

### Data

The database now holds **27 commonly dispensed medicines** with full detail:
molecular formula, formula weight, manufacturer (site and drug licence number),
Indian Pharmacopoeia and BP/USP monograph references, mechanism of action,
pharmacokinetics, pregnancy category, HSN/GST, and schedule classification.
There are **53 dosage guides** across five age bands, seeded automatically.

Opening stock levels are set per medicine. They deliberately include a few
low-stock and out-of-stock lines so the alerting is visibly working; treat them
as a starting point, not a purchasing recommendation.

### Interface

- **Animated startup screen** (separate from the application, shown once per
  browser session) carrying the creator attribution and a live identity-verified
  badge.
- **Dashboard cleaned up** — the self-promotional feature lists are gone,
  replaced by stock alerts, quick actions and an inventory summary.
- **Medicine detail view** covering every stored field, grouped into identity,
  chemistry, manufacturer, pharmacopoeia, clinical, pharmacokinetics and
  regulatory sections.
- **Patient record drawer** with allergies (add/remove), medical background,
  prescription history, and medicine suggestions per chronic condition.
- **Prescription writer** with live patient-safety screening as you add each
  medicine.
- Real patient/medicine pickers throughout instead of raw numeric IDs.

---

## Security and authorship protection

### What is actually enforced

- **Identity verification.** The creator block in `backend/app/branding.py`
  carries a sealed SHA3-256 signature. If the name, app name or version is
  edited without re-sealing, the application refuses to show the normal splash
  screen and displays a tamper notice instead.
- **Per-record integrity seals.** Every medicine carries a `record_hash` and a
  `content_seal` computed over 40 clinical fields. Each is re-verified on boot
  and on demand. A record edited outside the application is reported as
  `TAMPERED`.
- **Verification is visible.** `/api/security/verify` returns the full report,
  the dashboard shows an integrity badge, and the startup console prints the
  result.

### What is *not* enforced — please read this

**A locally installed program cannot prevent a determined person from changing
its data.** The sealing key ships inside the executable and can, in principle,
be extracted. What these seals give you is *detection*: tampering is
demonstrably reported rather than silently accepted. That is an honest and
useful guarantee; "cannot be changed by anyone" is not one that any
locally-installed software can truthfully offer.

If you need authorship that genuinely cannot be forged, the two real options
are:

1. **Authenticode code signing** with a private certificate. Signing is
   configured in `pharms.spec` (`codesign_identity`); the certificate is the
   thing you alone hold.
2. **Server-side verification**, where the application checks its integrity
   against a key held on a server you control.

Both are practical additions — say the word and I will wire either one up.

### Making an authorised change

```powershell
cd backend
.\venv\Scripts\python.exe init_db.py --verify       # see the current state
.\venv\Scripts\python.exe init_db.py --reseal-all   # re-seal after your edit
```

---

## Project layout

```
PharmacyMS/
├── backend/
│   ├── app/
│   │   ├── branding.py          creator identity + sealed signature
│   │   ├── security.py          integrity sealing and verification
│   │   ├── data/
│   │   │   ├── seed_medicines.py  the 27 medicines + 53 dosage guides
│   │   │   └── seeder.py          idempotent bootstrap + opening stock
│   │   ├── models/              Medicine, Patient, Prescription, Inventory
│   │   ├── routes/              REST blueprints (incl. security_routes.py)
│   │   └── services/            dosage, interactions, recommender
│   ├── desktop_app.py           native-window entry point for the .exe
│   ├── pharms.spec              PyInstaller specification
│   ├── pharms.ico               application icon
│   ├── build_exe.ps1            one-command build
│   ├── install_app.ps1          install + Desktop/Start Menu shortcuts
│   ├── import_medicines.py      bulk catalogue importer (CDSCO, Jan Aushadhi)
│   └── init_db.py               initialise / verify / re-seal
└── frontend/
    └── src/
        ├── components/SplashScreen.jsx   animated startup + tamper notice
        └── pages/                        dashboard, medicines, patients,
                                          prescriptions, inventory, dosage,
                                          recommender
```

---

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/medicines` | List / search medicines |
| GET | `/api/medicines/:id` | Full record incl. inventory and dosage guides |
| POST/PUT/DELETE | `/api/medicines[/:id]` | Manage medicines |
| GET | `/api/patients` | List / search patients |
| GET | `/api/patients/:id/profile` | Demographics + allergies + history + suggestions |
| POST/DELETE | `/api/patients/:id/allergies[/:aid]` | Manage allergies |
| GET/POST | `/api/prescriptions` | List / create prescriptions |
| GET | `/api/inventory/summary` | Stock counts and valuation |
| GET | `/api/inventory/alerts` | Low-stock, out-of-stock and expiry alerts |
| POST | `/api/recommender/safety-screen` | Combined allergy/contraindication/interaction/stock verdict |
| POST | `/api/recommender/dosage` | Age-appropriate dose calculation |
| POST | `/api/recommender/recommend-medicines` | Screened recommendations |
| GET | `/api/security/branding` | Creator attribution + identity status |
| GET | `/api/security/verify` | Full integrity report for all records |

---

## Selling licence keys (the ₹500 branding unlock)

There is **no payment system in this project** — you collect the money however
you prefer (UPI, bank transfer, Instamojo, Razorpay) and issue the key yourself.
The software side is complete and offline.

### One-time setup
Generate your own signing secret. This lives **outside** the project so it can
never be committed, and the shipping app never carries it:

```powershell
cd backend
.\venv\Scripts\python.exe setup_licence_secret.py
```

### For each customer
```powershell
# 1. Issue the key (records it against the pharmacy name)
.\venv\Scripts\python.exe issue_key.py "Sri Balaji Medicals"

# 2. Send them the key. They enter it under Branding in the app.

# 3. Before your next build, export the key table
.\venv\Scripts\python.exe issue_key.py --export
.\build_exe.ps1
```

Step 3 is what lets the shipped app verify the key. A build contains the *issued
key table*, never the signing secret — so the app can check a key without being
able to mint one.

```powershell
.\venv\Scripts\python.exe issue_key.py --list    # every key sold, with
                                                 # the running total in ₹
```

### What this protects against, honestly
| Scenario | Outcome |
|---|---|
| Customer edits the app to use their own name | Rejected — no valid key |
| Customer invents a key | Rejected — wrong HMAC tag |
| Customer's key used by a *different* pharmacy | Rejected — keys are name-bound |
| Keys survive reinstalls / new computer | Yes — same name, same key |
| Someone reverse-engineers the exe to extract an already-issued key | **Possible** |

That last row is the honest limit. A build must contain the issued keys in order
to verify them offline, so a determined attacker could extract one. What they
*cannot* do is mint a key for a **new** name — that needs your secret.

If you need keys that genuinely cannot be forged or shared, the app has to check
each activation against a server you control. That is a contained change to
`app/licensing.py`; ask and I will wire it up.

---

## Expanding the catalogue
India markets a very large number of formulations (six figures of brand variants
across roughly two thousand active ingredients) and there is no single
authoritative machine-readable file. The 40 medicines shipped here are a
curated, verified *dispensing* set. To load national coverage, use the importer
with a real source — CDSCO approved-drug lists, the Jan Aushadhi catalogue, NPPA
ceiling-price lists, or your own distributor sheet:

```powershell
cd backend
.\venv\Scripts\python.exe import_medicines.py --file catalogue.csv --dry-run
.\venv\Scripts\python.exe import_medicines.py --file catalogue.csv
```

The importer accepts CSV or JSON with flexible header names (`MRP`, `Company`,
`Indications`, `Generic Name` etc. are all recognised). Rows missing a required
field are **rejected with a reason** rather than padded with placeholders — a
half-empty record must never enter a clinical database looking complete.
Imported rows are sealed like any other, so `init_db.py --verify` reports them
as INTACT.

I deliberately did not generate entries to pad the count. Inventing dosages,
formulas and risk data for a medicine would be fabricating clinical information,
which is the one thing this project will not do.

---

## Medical disclaimer

This software is a record-keeping and reference tool. The dosing information is
derived from published adult reference doses and standard formulas; the
recommender applies allergy and contraindication filters. **None of it is a
substitute for professional clinical judgement.** Every calculated dose and
every recommendation is labelled as an estimate and must be verified by a
qualified prescriber before use. Verify all medicine data against the current
edition of the relevant pharmacopoeia and the manufacturer's own labelling
before relying on it.

---

## Configuration

| Variable | Purpose |
|---|---|
| `PHARMS_DATA_DIR` | Directory for `pharmacy.db`. Defaults to `%LOCALAPPDATA%\PharmMS` when installed, or `backend/app/` in development. |

The server binds to `127.0.0.1` only, so the database is never exposed to the
local network.

---

## Verified behaviour
Checked on this machine against the installed build:

- Desktop shortcut launches a native window titled *Pharmacy Management System*
- No console window appears
- The database is created at `%LOCALAPPDATA%\PharmMS\pharmacy.db` on first run,
  with a `backups\` folder beside it
- 40/40 medicine records verify as `INTACT`; creator identity verifies
- 69 dosage guides, 39 inventory lines, stock valuation in INR
- All 9 sections load with zero browser console errors
- Runs with no network access; the built bundle contains no external URLs
