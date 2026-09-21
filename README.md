# PharmMS — Pharmacy Management System

<p align="center">
 <img src="frontend/public/logo.png" alt="PharmMS" width="120" height="120">
</p>

<p align="center">
 <strong>Offline pharmacy management software for Windows.</strong><br>
  Inventory, patients, prescriptions, dosing reference and printed reports —
  all on your own computer, with no internet connection required.
</p>

<p align="center">
 <a href="../../releases/latest"><strong>⬇ Download the installer</strong></a>
</p>

---

## Download and install

1. Go to the [latest release](../../releases/latest)
2. Download **`PharmMS-Setup.exe`**
3. Double-click it and click **Install**

That is the whole process. No Python, no Node.js, **no administrator rights**,
and no internet connection are needed at any point.

The installer adds a **PharmMS** shortcut to your Desktop and Start Menu, and
registers itself under *Apps & features* so you can uninstall it normally.

> **Windows SmartScreen:** the installer is not code-signed, so Windows may warn
> you on first run. Click **More info** → **Run anyway**. Code signing needs a
> paid certificate — [open an issue](../../issues) if you would like it added.

### Where your data lives

Your records are stored at `%LOCALAPPDATA%\PharmMS\pharmacy.db` — deliberately
**outside** the program folder. Upgrading, reinstalling or moving the
application never touches your patient data, and uninstalling asks before
deleting anything.

---

## What it does

| Area | What you get |
|---|---|
| **Medicine database** | Molecular formulas, formula weights, manufacturers with drug licence numbers, Indian Pharmacopoeia and BP/USP monograph references, mechanism of action, pharmacokinetics, pregnancy categories, HSN/GST and schedule classification |
| **Patients** | Records with allergy tracking that flags **within-class cross-reactivity** — a penicillin allergy correctly blocks amoxicillin |
| **Prescriptions** | Write, screen and print. Safety checks run live as you add each medicine |
| **Printed reports** | Prescriptions and full patient histories on **your own pharmacy letterhead** with your logo. Prescriptions follow the classical pharmacopoeial structure — superscription (℞), inscription, subscription, signatura — with the statutory **Schedule H1 red-box warning**, prescriber registration number and dual signature blocks |
| **Dosage calculator** | Age-based dosing using Young's rule, labelled as an estimate with a confidence flag |
| **Alternatives finder** | "What else treats this?" — ranked by indications overlap, drug class and price, screened against the patient |
| **Inventory** | Stock levels, batch and expiry tracking, low-stock alerts, valuation in ₹ |
| **Backups** | Automatic snapshots on every launch, plus one-click export and restore |

### Built for offline use

Verified: the application makes **no internet requests**. No CDN fonts, no
analytics, no telemetry, no cloud sync. It runs normally with networking
completely disabled, which is what a pharmacy counter needs.

---

## Custom branding — ₹500 one-time

Want the app and every printed prescription to carry **your pharmacy's name and
logo** instead of the default?

1. Open PharmMS and go to the **Branding** tab
2. Enter your pharmacy name and the licence key issued for it
3. Upload your logo, add your address, phone, drug licence number and GSTIN

Your details then appear on the app's startup screen and on every printed
prescription and patient report.

**Request a key** by [opening an issue](../../issues/new) with your pharmacy
name and your payment reference. It is a **one-time ₹500**. Keys are:

- **Bound to your pharmacy name** — a key issued for one shop will not work for another
- **Verified offline** — no activation server, no phone-home, works without internet
- **Yours to keep** — moving to a new computer just means entering the same key again

The app stays fully functional without a key; it simply keeps the default
branding. **Nothing about patient care, records or printing is gated** — only
your pharmacy's own name and logo.

> **Payment is handled separately.** This repository contains no payment
> processing. Open an issue with your pharmacy name and the maintainer will
> reply with payment instructions and your key.

---

## Documentation
| Document | For |
|---|---|
| [`INSTALLATION_GUIDE.md`](INSTALLATION_GUIDE.md) | Installing, uninstalling, backing up, moving to a new PC |
| [`USAGE_GUIDE.md`](USAGE_GUIDE.md) | A walkthrough of every screen in the app |
| [`DEVELOPER_NOTES.md`](DEVELOPER_NOTES.md) | Building, publishing, licence keys, bug history |

---

## Screenshots

*(Add screenshots here after your first run — `docs/screenshot-dashboard.png`,
`docs/screenshot-prescription.png`, `docs/screenshot-branding.png`.)*

---

## For developers

<details>
<summary><strong>Build from source</strong></summary>

Requires Python 3.10+, Node.js 18+ and Windows.

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Frontend
cd ..\frontend
npm install
npm run build
cd ..\backend

# Application + installer
.\build_exe.ps1            # -> dist\PharmMS.exe   (the application)
.\build_installer.ps1      # -> dist\PharmMS-Setup.exe (the distributable)
```

### Running in development

```powershell
# Terminal 1 - API on :5000
cd backend
.\venv\Scripts\python.exe run.py

# Terminal 2 - React dev server on :3000 (hot reload)
cd frontend
npm start
```

</details>

<details>
<summary><strong>Project structure</strong></summary>

```
PharmacyMS/
├── backend/
│   ├── app/
│   │   ├── branding.py          creator identity, sealed
│   │   ├── licensing.py         licence keys + pharmacy branding
│   │   ├── security.py          per-record integrity seals
│   │   ├── data/                medicine reference set + seeder
│   │   ├── models/              Medicine, Patient, Prescription, Inventory
│   │   ├── routes/              REST API blueprints
│   │   └── services/            dosage, interactions, alternatives, storage
│   ├── desktop_app.py           native window entry point
│   ├── build_exe.ps1            build the application
│   ├── build_installer.ps1      build the setup .exe
│   ├── create_github_repo.ps1   create the GitHub repo + first release
│   ├── publish_github.ps1       push code and upload a release
│   ├── import_medicines.py      bulk catalogue importer
│   └── make_logo.py             regenerate logo assets
├── .github/workflows/
│   └── build-installer.yml      CI: build the .exe on a tag push
└── frontend/
    └── src/pages/                dashboard, medicines, patients,
                                  prescriptions, inventory, dosage,
                                  recommender, alternatives, data, branding
```

</details>

<details>
<summary><strong>Adding medicines in bulk</strong></summary>

The shipped database is a curated, verified dispensing set. To load national
coverage, import a real catalogue — CDSCO approved-drug lists, the Jan Aushadhi
catalogue, NPPA ceiling-price lists, or your own distributor sheet:

```powershell
cd backend
.\venv\Scripts\python.exe import_medicines.py --file catalogue.csv --dry-run
.\venv\Scripts\python.exe import_medicines.py --file catalogue.csv
```

CSV or JSON, flexible column names (`MRP`, `Company`, `Indications`, `Generic
Name` are all recognised). **Rows missing a required field are rejected with a
reason** rather than padded with placeholders — a half-empty record must never
enter a clinical database looking complete.

</details>

<details>
<summary><strong>Publishing to GitHub</strong></summary>

### First time — create the repository and ship a release
```powershell
$env:GITHUB_TOKEN = "ghp_your_token"     # repo scope
cd backend
.\create_github_repo.ps1 -Repo "yourname/pharms"
```

That single command creates the GitHub repository, connects `origin`, commits
the source, builds `PharmMS-Setup.exe` and publishes it as a release asset.
Add `-DryRun` first to see every step without contacting GitHub, or
`-SkipRelease` to publish the code without building the installer.

### Later releases
```powershell
cd backend
.\publish_github.ps1 -Repo "yourname/pharms" -Tag v2.0.1
```

### Releases built by GitHub, not by you
`.github/workflows/build-installer.yml` builds the installer on GitHub's own
Windows runners and attaches it to the release. **Push an annotated tag and the
installer appears, with nothing built on your machine:**

```powershell
git tag v2.0.0
git push origin v2.0.0
```

You can also run it by hand from *Actions → Build installer → Run workflow*; the
installer is then downloadable from the run's *Artifacts* section even without a
release.

The workflow needs no secrets — it uses the automatic `GITHUB_TOKEN` — and it
runs the same `build_installer.ps1` you do, so a green build proves the
documented command works.

Your database, `.env` files and the private key-issuing tool are excluded by
`.gitignore` — patient data must never reach a public repository.

</details>

---

## Medical disclaimer

This software is a record-keeping and reference tool. Dosing information is
derived from published adult reference doses and standard formulas; the
recommender applies allergy and contraindication filters. **None of it is a
substitute for professional clinical judgement.** Every calculated dose and
recommendation is labelled as an estimate and must be verified by a qualified
prescriber. Verify all medicine data against the current edition of the relevant
pharmacopoeia and the manufacturer's labelling before relying on it.

---

**Designed & Developed by Jayant**
