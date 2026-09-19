# PharmMS — Installation & Deployment Guide

**Designed & Developed by Jayant**

---

## For pharmacies (the normal case)

### Requirements

| | |
|---|---|
| **Operating system** | Windows 10 or 11 (64-bit) |
| **Disk space** | ~60 MB for the program, plus your data |
| **RAM** | 2 GB |
| **Internet** | **Not required** — the app is fully offline |
| **Administrator rights** | **Not required** |

You do **not** need Python, Node.js, a database server, or any other software
installed. Everything the application needs is inside the single installer file.

### Install

1. Download **`PharmMS-Setup.exe`** from the
   [latest release](https://github.com/YOUR-USERNAME/pharms/releases/latest)
2. Double-click it
3. Click **Install**

The wizard installs to your user folder and creates a **PharmMS** shortcut on
your Desktop and in your Start Menu. Nothing outside your own user account is
modified.

### Windows SmartScreen warning

On first run Windows may show:

> *Windows protected your PC*

This appears because the installer is not code-signed — code signing requires a
paid certificate. To proceed:

**More info** → **Run anyway**

This happens once per download.

### Where your data lives

```
%LOCALAPPDATA%\PharmMS\pharmacy.db      your patient and stock records
%LOCALAPPDATA%\PharmMS\backups\         automatic snapshots
```

Your records are deliberately kept **outside** the program folder. Installing an
update, reinstalling, or moving the application never touches your data.

To see the exact path on your machine, open the app and go to **Data**.

### Uninstall

*Settings → Apps → Installed apps → Pharmacy Management System → Uninstall*

The uninstaller asks whether to delete your records. Say **No** if you are
upgrading or reinstalling and want to keep them.

---

## Backing up

Open the **Data** tab in the app.

| Action | What it does |
|---|---|
| **Take snapshot** | Copies the current database into `backups\`. One is also taken automatically every time the app starts. |
| **Download export** | Writes a portable JSON file with every record. Keep it anywhere — a USB drive, another PC, cloud storage. |
| **Import** | Loads an export back in. Additive: existing records are kept. |
| **Restore** | Rolls the database back to an earlier snapshot. A safety snapshot is taken first, so a restore can itself be undone. |

The last 10 automatic snapshots are kept; older ones are pruned.

**If you move to a new computer:** install PharmMS there, then use **Import**
with your exported JSON file. Your licence key works on the new machine too —
just enter the same pharmacy name and key.

---

## Branding your pharmacy name and logo

The app ships with a default name and logo. To put your own on it:

1. Open the app → **Branding**
2. Enter your pharmacy name and the licence key issued for it
3. Upload your logo and fill in your address, phone, drug licence number and GSTIN

Your name and logo then appear on the startup screen, in the app header, and on
every printed prescription and patient report.

- Keys are a **one-time ₹500**
- **Bound to your pharmacy name** — a key issued for one shop will not work for another
- **Verified offline** — no activation server, works without internet
- The app works fully without a key; it just keeps the default branding

Request a key by [opening an issue](https://github.com/YOUR-USERNAME/pharms/issues/new)
with your pharmacy name and payment reference. Payment itself is arranged
separately — this software contains no payment processing.

---

## Printing

Prescriptions, full patient records and stock lists print on your letterhead.

Open a patient or prescription and click **Print**. The document opens in a
print-ready A4 view with a **Print / Save as PDF** button. Use your browser or
Windows print dialog, and choose *Save as PDF* if you want a file instead of
paper.

Set your pharmacy details under **Branding** first — otherwise the header shows
the default name.

---

## For developers

### Build from source

Requires Python 3.10+, Node.js 18+, and Windows.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..\frontend
npm install
npm run build
cd ..\backend
```

| Command | Produces |
|---|---|
| `.\build_exe.ps1` | `dist\PharmMS.exe` — the application, with its own window |
| `.\build_installer.ps1` | `dist\PharmMS-Setup.exe` — the single distributable |
| `.\install_app.ps1` | Installs locally with Desktop and Start Menu shortcuts |
| `.\install_app.ps1 -Uninstall` | Removes it, keeping your data |

### Development mode

```powershell
# Terminal 1 — API on :5000
cd backend
.\venv\Scripts\python.exe run.py

# Terminal 2 — React dev server on :3000, with hot reload
cd frontend
npm start
```

The frontend detects the port: on `:3000` it calls the API on `:5000`, otherwise
it uses same-origin `/api`, which is how the packaged build works.

### Publishing a release

```powershell
$env:GITHUB_TOKEN = "ghp_your_token"      # needs "repo" scope
cd backend
.\publish_github.ps1 -Repo "yourname/pharms" -Tag v2.0.0
```

Commits the source, builds the installer, and uploads `PharmMS-Setup.exe` as a
release asset.

**Your patient database and the private key-issuing tool are excluded by
`.gitignore`.** Never commit `pharmacy.db` or `issued_keys.json`.

### Licence keys

One-time setup, then per customer:

```powershell
.\venv\Scripts\python.exe setup_licence_secret.py         # once
.\venv\Scripts\python.exe issue_key.py "Their Pharmacy"   # per sale
.\venv\Scripts\python.exe issue_key.py --export           # before each build
.\build_exe.ps1
```

Full detail, including what this does and does not protect against, is in
`DEVELOPER_NOTES.md`.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| SmartScreen blocks the installer | Not code-signed. **More info → Run anyway**. |
| Nothing happens when I double-click the app | It opens in a window that may take a few seconds on first run. If nothing appears, check Task Manager for `PharmMS`. |
| "Port 5000 in use" | The app picks another port automatically. If it cannot start at all, close other copies. |
| Prescriptions show the wrong pharmacy name | Set your details under **Branding**, and make sure a valid licence key is entered. |
| I lost my data | Open **Data** and restore a snapshot. Snapshots are taken automatically on every start. |
| Moving to a new PC | Install PharmMS, then **Import** your exported JSON file. Re-enter your licence key. |
| Antivirus flags the app | Unsigned executables are sometimes flagged. Add an exclusion, or build from source yourself. |

---

## Medical disclaimer

This software is a record-keeping and reference tool. Dosing information is
derived from published adult reference doses and standard formulas; the
recommender applies allergy and contraindication filters. **None of it is a
substitute for professional clinical judgement.** Every calculated dose and
recommendation is labelled as an estimate and must be verified by a qualified
prescriber. Verify all medicine data against the current edition of the relevant
pharmacopoeia and the manufacturer's labelling before relying on it.
