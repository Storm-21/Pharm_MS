# PharmMS — Using the Application

**Designed & Developed by Jayant**

A walkthrough of every screen. If you have not installed it yet, see
`INSTALLATION_GUIDE.md`.

---

## Launching

Double-click **PharmMS** on your Desktop, or find it in the Start Menu. It opens
in its own window and takes a few seconds on first run.

---

## Dashboard

Your starting screen. Everything is live — nothing on it is a placeholder.

- **Four counters** — medicines on file, registered patients, lines needing
  reorder, expired batches. Click any card to jump to the relevant screen.
- **Integrity badge** (top right) — confirms the medicine reference data has not
  been altered outside the application. Green means verified.
- **Stock alerts** — the low-stock, out-of-stock and expiry lines that need
  attention, newest first.
- **Quick actions** — shortcuts to the tasks you do most.
- **At a glance** — stock position summary in ₹.

---

## Medicine Database

Every medicine you stock, with full detail.

**Search** by name, generic name or brand. Click the eye icon on any row for the
complete record, grouped into:

| Section | Contents |
|---|---|
| Identity | Brand, strength, dosage form, route, storage, prescription status |
| Composition & chemistry | Salt composition, **molecular formula**, formula weight, therapeutic and pharmacological class |
| Manufacturer | Manufacturer, manufacturing site, **drug licence number**, marketed by, country of origin |
| Pharmacopoeia | **Indian Pharmacopoeia** reference, BP/USP reference, IP status, monograph notes |
| Clinical use | Indications, mechanism of action, side effects, contraindications, warnings, drug and food interactions, pregnancy category |
| Pharmacokinetics | Onset, half-life, bioavailability, protein binding, metabolism, excretion, maximum daily dose |
| Regulatory & commercial | Schedule, HSN code, GST rate, barcode, cost and selling price |
| Stock on hand | Every batch with quantity, expiry and shelf location |

Add, edit or delete with the buttons on each row. Records you add are sealed
like the built-in ones, so the integrity check covers them too.

> **Tip:** to load a large catalogue (CDSCO, Jan Aushadhi, your distributor's
> price list) use `import_medicines.py` rather than typing entries in. See
> `DEVELOPER_NOTES.md`.

---

## Patients

**Adding a patient** — click *Add patient*. Only name, date of birth and gender
are required. Two fields do real work:

- **Chronic conditions** — drives the condition-based medicine suggestions in
  the patient record. Enter them comma-separated, e.g. `Diabetes, Hypertension`
- **Current medications** — used for drug-interaction screening when you write a
  prescription, e.g. `Metformin, Lisinopril`

**The patient record** (click *View* on any card) shows:

- Summary tiles — allergies, prescriptions, conditions
- **Allergies** with severity, and an add/remove form. These are checked
  *clinically*, not by text match: recording a **Penicillin** allergy correctly
  blocks Amoxicillin and other beta-lactams
- Medical background
- **Suggested medicines per condition**, screened against the patient's allergies
- Complete **prescription history**
- **Print full report** — the entire record on your letterhead

---

## Prescriptions

**Writing one** — click *New prescription*:

1. Pick the **patient** — their allergies and current medications appear
   immediately so you can see them while prescribing
2. Enter the prescriber and diagnosis
3. Add each medicine. As soon as you select one, it is **screened live** against
   that patient:
   - red **Blocked** — an allergy or contraindication matches
   - green **No allergy or contraindication found**
   - warnings for interactions with their current medications, and out-of-stock
4. The dose is pre-filled from the patient's age where a guide exists — adjust it
5. **Save**

Adding a blocked medicine is possible but asks you to confirm first, so a
contraindicated combination cannot be recorded by accident.

**Printing** — click **Print** on any prescription (or the printer icon in the
list). It opens an A4 document on your pharmacy letterhead with the patient
details, every medicine with its salt composition, dosage and instructions, any
allergy warning, and signature lines. Use *Print / Save as PDF*.

---

## Dosage Calculator

Select a patient and a medicine, optionally the condition, and calculate.

You get the dose, frequency, duration and total quantity needed, plus:

- **Where the number came from** — which formula was applied. Where no dosage
  guide is stored, Young's rule is used and the result is explicitly labelled an
  **estimate** with a confidence flag
- **Safety verdict** — allergy, contraindication, interaction and stock status in
  one panel
- **Drug cycle** — whether a course needs completing, tapering, or a break

Every result is labelled as guidance to verify, not a prescribing decision.

---

## Alternatives

Two ways to answer *"what else could be used?"*

**By medicine** — pick a medicine and see others for the same condition, ranked
by indications overlap and drug class, with price difference and stock shown side
by side.

**By condition** — type a condition (e.g. `Hypertension`, `Diabetes`) to see
everything you stock for it, **grouped by drug class**, cheapest first.

Select a patient and every result is screened — unsafe options are flagged and
sorted to the bottom rather than hidden.

---

## Inventory

Stock position with counts and valuation, status filters (in stock, low, out,
expired), batch numbers, expiry dates and shelf locations.

- **+10 / −5** buttons adjust stock quickly for receiving and dispensing
- **Add stock** records a new batch with its batch number, dates and location
- **Stock alerts** at the top list what needs reordering or has expired

---

## Recommender

Enter a patient and a condition to get ranked medicine suggestions, screened
against their allergies and medical history, with a recommendation score and the
reasoning shown. Useful for a patient with no history to draw on.

---

## Data & backups

**Shows exactly where your records are**, so the location is never a mystery.

| Button | Effect |
|---|---|
| **Take snapshot** | Copies the database into `backups\`. Also happens automatically every time the app starts. |
| **Download export** | A portable JSON file with everything — keep it on a USB drive or another PC |
| **Choose file** (import) | Loads an export. Additive: existing records are kept |
| **Restore** | Rolls back to an earlier snapshot. A safety snapshot is taken first, so a restore can itself be undone |

The last 10 automatic snapshots are kept.

**Moving to a new computer:** install PharmMS there, then *Choose file* with your
exported JSON. Re-enter your licence key afterwards.

---

## Branding

Where you put **your** pharmacy's identity on the application.

1. Enter your pharmacy name and the licence key issued for it → **Activate licence**
2. **Upload logo** — PNG, JPG, SVG or WEBP, up to 2 MB. Around 512×512 px works
   best on printouts
3. Fill in address, phone, email, drug licence number, GSTIN, pharmacist name and
   a prescription footer note

These appear on the startup screen and on every printed prescription and patient
report.

Without a key the app keeps the default branding. **Nothing about patient care,
records or printing is locked** — only the shop's own name and logo.

---

## Keyboard and browser tips

- The app works offline; there is no sync and no login
- **Ctrl+P** prints the page you are on, but use the in-app **Print** buttons for
  correctly formatted documents
- To keep a PDF instead of paper, choose *Save as PDF* in the print dialog

---

## Common questions

**Can two people use it at once?**
Not from the same data file. Each installation keeps its own records. For a
shared setup across counters you would need a server-based deployment — ask.

**What happens if I lose my computer?**
Restore from your exported JSON file on a new machine. That is why the Data tab
offers an export: a snapshot only helps if the disk survives.

**Is my patient data sent anywhere?**
No. The application makes no internet requests at all. Open the Data tab and it
tells you the exact file path — you can confirm it yourself.

**Can I add my own medicines?**
Yes, either one at a time in the Medicine Database, or in bulk with
`import_medicines.py`.

---

## Medical disclaimer

This software is a record-keeping and reference tool. Dosing information is
derived from published adult reference doses and standard formulas; the
recommender applies allergy and contraindication filters. **None of it is a
substitute for professional clinical judgement.** Every calculated dose and
recommendation is labelled as an estimate and must be verified by a qualified
prescriber before use.
