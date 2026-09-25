"""
Printable prescription / patient report.

Produces a self-contained HTML document with the pharmacy's own name, logo and
contact details in the header, laid out for A4 printing. The browser's own
print dialog handles "Save as PDF", which avoids adding a PDF library and keeps
the output identical to what appears on screen.

Everything is escaped before it reaches the template - patient and medicine
names are free text and would otherwise be an injection point.
"""

from datetime import datetime
from html import escape

from flask import Blueprint, jsonify, Response, request

from app import licensing
from app.models import Patient, Prescription, Medicine, PrescriptionItem

report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


def _e(value):
    """Escape for HTML, tolerating None."""
    return escape(str(value)) if value not in (None, '') else ''


def _dotted(value, fallback='&mdash;'):
    # Escaped value, or an em-dash placeholder for an empty field.
    text = _e(value)
    return text if text else fallback

def _schedule_h1(medicines):
    # True when any prescribed medicine is a Schedule H1 drug.
    #
    # Schedule H1 (Drugs and Cosmetics Rules, inserted by G.S.R. 588(E), 2013)
    # carries extra duties at dispensing: a separate register entry, retention
    # of the prescription for three years, and a red-box warning on the label.
    # The printed prescription should therefore carry that warning too.
    for medicine in medicines:
        schedule = (medicine.schedule_classification or '').lower() if medicine else ''
        if 'h1' in schedule.replace(' ', '').replace('-', ''):
            return True
    return False

def _brand_header():
    branding = licensing.branding_settings()
    licensed = branding.get('licensed')
    name = branding.get('pharmacy_name') if licensed else branding.get('product_name')
    logo_url = '/api/branding/logo' if branding.get('has_custom_logo') else '/logo.png'

    contact_bits = []
    if branding.get('pharmacy_address'):
        contact_bits.append(_e(branding['pharmacy_address']))
    if branding.get('pharmacy_phone'):
        contact_bits.append('Phone: ' + _e(branding['pharmacy_phone']))
    if branding.get('pharmacy_email'):
        contact_bits.append('Email: ' + _e(branding['pharmacy_email']))
    if branding.get('pharmacy_registration_no'):
        contact_bits.append('D.L. No: ' + _e(branding['pharmacy_registration_no']))
    if branding.get('pharmacy_gstin'):
        contact_bits.append('GSTIN: ' + _e(branding['pharmacy_gstin']))

    return {
        'name': _e(name) or _e(branding.get('product_name')),
        'logo_url': logo_url,
        'contact': ' &nbsp;&bull;&nbsp; '.join(contact_bits),
        'pharmacist': _e(branding.get('pharmacist_name')),
        'footer': _e(branding.get('prescription_footer')),
        'licensed': licensed,
        'creator': _e(branding.get('creator_name')),
        'product': _e(branding.get('product_name')),
        # Prescriber block for the standard prescription layout.
        'prescriber_name': _e(branding.get('prescriber_name')),
        'prescriber_qualifications': _e(branding.get('prescriber_qualifications')),
        'prescriber_registration_no': _e(branding.get('prescriber_registration_no')),
        'prescriber_contact': _e(branding.get('prescriber_contact')),
        'pharmacist_registration_no': _e(branding.get('pharmacist_registration_no')),
        'address': _e(branding.get('pharmacy_address')),
        'phone': _e(branding.get('pharmacy_phone')),
        'email': _e(branding.get('pharmacy_email')),
        'registration_no': _e(branding.get('pharmacy_registration_no')),
        'gstin': _e(branding.get('pharmacy_gstin')),
    }


BASE_CSS = """
  @page { size: A4; margin: 12mm; }
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #111827; margin: 0; padding: 24px; background: #f3f4f6;
    font-size: 12.5px; line-height: 1.45;
  }
  .sheet {
    max-width: 210mm; margin: 0 auto; background: #fff; padding: 12mm;
    box-shadow: 0 1px 3px rgba(0,0,0,.12); position: relative;
  }
  /* Faint paper guilloche - the fine engraved border a real prescription pad
     carries. Kept very light so it never competes with the text. */
  .sheet::before {
    content: ""; position: absolute; inset: 5mm; pointer-events: none;
    border: 1px solid #e8e2d6;
    background-image:
      repeating-linear-gradient(45deg, #faf7f0 0 1px, transparent 1px 7px),
      repeating-linear-gradient(-45deg, #faf7f0 0 1px, transparent 1px 7px);
    opacity: .55;
  }
  .sheet > * { position: relative; }
  .head { display: flex; gap: 18px; align-items: flex-start;
          border-bottom: 3px solid #2563eb; padding-bottom: 14px; }
  .head img { width: 74px; height: 74px; object-fit: contain; flex: 0 0 auto; }
  .head .titles { flex: 1; min-width: 0; }
  .head h1 { margin: 0 0 4px; font-size: 25px; color: #1e3a8a; letter-spacing: .2px; }
  .head .contact { color: #4b5563; font-size: 11.5px; }
  .head .pharmacist { color: #374151; font-size: 11.5px; margin-top: 3px; }
  .doc-title { margin: 14px 0 10px; font-size: 14px; font-weight: 700;
               text-transform: uppercase; letter-spacing: .09em; color: #374151; }
  .grid { display: flex; flex-wrap: wrap; gap: 4px 26px; margin-bottom: 14px; }
  .grid div { min-width: 150px; }
  .label { color: #6b7280; font-size: 10.5px; text-transform: uppercase;
           letter-spacing: .06em; }
  .value { font-weight: 600; }
  table { width: 100%; border-collapse: collapse; margin-top: 6px; }
  th { background: #eff6ff; color: #1e3a8a; text-align: left; font-size: 11px;
       text-transform: uppercase; letter-spacing: .05em;
       padding: 7px 9px; border-bottom: 1px solid #bfdbfe; }
  td { padding: 7px 9px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
  tr:nth-child(even) td { background: #fbfdff; }
  .section { margin-top: 16px; }
  .section h3 { font-size: 12px; text-transform: uppercase; letter-spacing: .07em;
                color: #374151; margin: 0 0 6px; }
  .notes { background: #f9fafb; border-left: 3px solid #93c5fd;
           padding: 8px 11px; font-size: 12px; color: #374151; }
  .alert { background: #fef2f2; border-left: 3px solid #ef4444;
           padding: 8px 11px; font-size: 12px; color: #991b1b; margin-bottom: 5px; }
  .ok { background: #f0fdf4; border-left: 3px solid #22c55e;
        padding: 8px 11px; font-size: 12px; color: #166534; }
  .sign { margin-top: 26px; display: flex; justify-content: space-between;
          gap: 20px; align-items: flex-end; }
  .sign div { border-top: 1px solid #9ca3af; padding-top: 5px;
              width: 200px; font-size: 11.5px; color: #4b5563; text-align: center; }
  .foot { margin-top: 18px; border-top: 1px solid #e5e7eb; padding-top: 9px;
          color: #6b7280; font-size: 10.5px; text-align: center; }

  /* ======================================================================
     Prescription - laid out in the classical order a pharmacist is trained
     to read in, which is also the order the courts and drug inspectors expect
     to find it in:

       1. Prescriber identity      5. Inscription  (medicines)
       2. Date                     6. Subscription (direction to pharmacist)
       3. Patient details          7. Signatura    (direction to patient, "Sig.")
       4. Superscription (Rx)      8. Renewal / prescriber signature
     ====================================================================== */

  /* --- 1. Prescriber block ("letterhead of the surgery") ---------------- */
  .prescriber { border: 1px solid #d7d2c4; border-bottom: none;
                background: #fdfcf8; padding: 9px 12px; margin-bottom: 0;
                font-size: 11.5px; color: #374151; }
  .prescriber .who { font-weight: 700; color: #1e3a8a; font-size: 14px;
                     letter-spacing: .01em; }
  .prescriber .qual { color: #4b5563; font-size: 11px; font-style: italic; }
  .prescriber .line { color: #4b5563; }
  .prescriber .dega { float: right; text-align: right; font-size: 10.5px;
                      color: #4b5563; line-height: 1.5; }
  .prescriber .dega b { color: #1e3a8a; }
  .clear { clear: both; }

  /* --- 2/3. Date band + patient identification -------------------------- */
  .meta-band { display: flex; border: 1px solid #d7d2c4; border-bottom: none;
               background: #fff; font-size: 11.5px; }
  .meta-band .cell { flex: 1; padding: 6px 12px; border-right: 1px solid #e8e2d6; }
  .meta-band .cell:last-child { border-right: none; }
  .meta-band .cell.right { text-align: right; }
  .meta-band .k { color: #6b7280; font-size: 9.5px; text-transform: uppercase;
                  letter-spacing: .07em; display: block; }
  .meta-band .v { font-weight: 600; color: #111827; }

  .patient-table { width: 100%; border-collapse: collapse; margin-bottom: 0;
                   font-size: 11.5px; border: 1px solid #d7d2c4; border-bottom: none; }
  .patient-table td { border-right: 1px solid #e8e2d6; padding: 5px 12px;
                      border-bottom: 1px solid #e8e2d6; vertical-align: top; }
  .patient-table td:last-child { border-right: none; }
  .patient-table .k { background: #faf8f3; color: #6b7280; font-size: 9.5px;
                      text-transform: uppercase; letter-spacing: .07em;
                      width: 13%; font-weight: 600; }
  .patient-table .v { font-weight: 600; width: 24%; }

  /* --- 4. Superscription ------------------------------------------------- */
  .rx-line { display: flex; align-items: center; justify-content: space-between;
             gap: 16px; margin: 12px 0 6px; }
  .rx { font-size: 38px; font-weight: 700; color: #1e3a8a; line-height: 1;
        font-family: "Cambria Math", "Segoe UI Symbol", Ebrima, serif; }
  .rx sup { font-size: 15px; }
  .rx-meta { font-size: 11px; color: #6b7280; text-align: right; }
  .rx-meta strong { color: #374151; }

  /* --- 5. Inscription ---------------------------------------------------- */
  .inscription { border: 1px solid #d7d2c4; overflow: hidden; }
  .inscription table { margin: 0; }
  .inscription th { background: #faf8f3; color: #1e3a8a; border-bottom: 1px solid #d7d2c4; }
  .rx-num { font-weight: 700; color: #1e3a8a; text-align: center; width: 30px; }
  .rx-num::after { content: ")"; }
  .sig { font-family: Georgia, "Times New Roman", serif; font-style: italic;
         color: #1f2937; font-size: 12px; }
  .sig .lat { font-style: normal; font-weight: 600; letter-spacing: .04em; }

  /* --- 6/7. Subscription + signatura + renewal --------------------------- */
  .subscription { margin-top: 10px; border: 1px solid #d7d2c4;
                  border-left: 4px solid #1e3a8a; background: #fbfaf6;
                  padding: 8px 12px; font-size: 11.5px; color: #374151; }
  .subscription .head { font-weight: 700; color: #1e3a8a; font-size: 10.5px;
                        text-transform: uppercase; letter-spacing: .08em;
                        margin-bottom: 4px; }
  .renewal { margin-top: 8px; font-size: 11.5px; color: #374151;
             border: 1px dashed #d7d2c4; padding: 6px 12px; background: #fff; }
  .renewal b { color: #b91c1c; }

  /* --- Schedule H1 red-box warning, as the label itself must carry ------- */
  .h1-box { margin-top: 10px; border: 2px solid #dc2626; padding: 6px 10px;
            font-size: 10.5px; color: #991b1b; background: #fff7f7; }
  .h1-box .t { font-weight: 700; text-transform: uppercase;
               letter-spacing: .06em; color: #b91c1c; }

  .legend { margin-top: 10px; font-size: 10px; color: #6b7280;
            border-top: 1px solid #e8e2d6; padding-top: 7px; }
  .legend b { color: #374151; }
  .legend .cols { display: flex; flex-wrap: wrap; gap: 2px 18px; margin-top: 3px; }
  .legend .cols span { min-width: 150px; }

  .flash { float: right; color: #b91c1c; font-weight: 700; font-size: 10px;
           border: 1px solid #fecaca; background: #fef2f2; border-radius: 4px;
           padding: 2px 7px; text-transform: uppercase; letter-spacing: .06em; }
  .section h3 { border-bottom: 1px solid #e8e2d6; padding-bottom: 3px; }

  .toolbar { max-width: 210mm; margin: 0 auto 14px; display: flex; gap: 8px;
             justify-content: flex-end; }
  .toolbar button, .toolbar a {
    font: inherit; font-size: 12px; padding: 8px 15px; border-radius: 7px;
    border: 1px solid #d1d5db; background: #fff; color: #374151;
    cursor: pointer; text-decoration: none;
  }
  .toolbar button.primary { background: #2563eb; border-color: #2563eb; color: #fff; }

  @media print {
    body { background: #fff; padding: 0; }
    .sheet { box-shadow: none; padding: 0; max-width: none; }
    .sheet::before { display: none; }
    .toolbar { display: none; }
    tr:nth-child(even) td { background: transparent; }
    .prescriber, .meta-band, .patient-table, .inscription, .subscription,
    .renewal, .h1-box { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .inscription tr { page-break-inside: avoid; }
  }
"""


TOOLBAR = """
<div class="toolbar">
 <a href="javascript:window.close()">Close</a>
 <button class="primary" onclick="window.print()">Print / Save as PDF</button>
</div>
"""


def _page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_e(title)}</title>
<style>{BASE_CSS}</style>
</head>
<body>
{TOOLBAR}
{body}
</body>
</html>"""


def _header(brand, doc_title):
    pharmacist = (f'<div class="pharmacist">Pharmacist: {brand["pharmacist"]}</div>'
                  if brand['pharmacist'] else '')
    # The title band is optional: the prescription layout carries its own
    # headings, so an empty doc_title must not leave a blank rule behind.
    title_band = (f'<div class="doc-title">{_e(doc_title)}</div>'
                  if doc_title else '')
    return f"""
<div class="head">
 <img src="{brand['logo_url']}" alt="Logo">
 <div class="titles">
    <h1>{brand['name']}</h1>
    <div class="contact">{brand['contact']}</div>
    {pharmacist}
 </div>
</div>
{title_band}"""""


def _footer(brand):
    extra = f'<div>{brand["footer"]}</div>' if brand['footer'] else ''
    attribution = ''
    if not brand['licensed']:
        attribution = (
            f'<div style="margin-top:4px">'
            f'{brand["product"]} &mdash; developed by {brand["creator"]}'
            f'</div>'
        )
    return f"""
<div class="foot">
  {extra}
 <div>Generated {datetime.now().strftime('%d %b %Y at %H:%M')}</div>
  {attribution}
</div>"""


@report_bp.route('/prescription/<int:prescription_id>', methods=['GET'])
def prescription_report(prescription_id):
    """Printable prescription for one visit, on the pharmacy's own letterhead."""
    prescription = Prescription.query.get_or_404(prescription_id)
    patient = Patient.query.get(prescription.patient_id)
    brand = _brand_header()

    medicines = [Medicine.query.get(i.medicine_id) for i in prescription.items]

    # --- 2. Date / reference ------------------------------------------------
    # The reference number identifies this sheet in the dispensing register, so
    # it is derived first and shown in the prescriber block and the date band.
    issued = prescription.created_at or datetime.now()
    reference = f'RX-{issued.year}-{prescription.id:05d}'

    # --- 1. Prescriber block (the "surgery letterhead") ---------------------
    # Prefer explicitly recorded prescriber details; fall back to the free-text
    # prescriber name stored on the prescription itself. A printed prescription
    # is not complete without the prescriber's name, qualification and
    # registration number, so a missing field shows a placeholder rather than
    # being silently dropped.
    prescriber_name = brand['prescriber_name'] or _e(prescription.doctor_name)
    prescriber_sub = ''
    if brand['prescriber_qualifications']:
        prescriber_sub += f'<div class="qual">{_e(brand["prescriber_qualifications"])}</div>'
    if brand['prescriber_registration_no']:
        prescriber_sub += ('<div class="line">Reg. No.: <strong>'
                           + brand['prescriber_registration_no'] + '</strong>'
                           + (' &nbsp;&bull;&nbsp; ' + brand['prescriber_contact']
                              if brand['prescriber_contact'] else '')
                           + '</div>')
    else:
        prescriber_sub += '<div class="line">Reg. No.: &mdash;</div>'

    prescriber_block = f"""
<div class="prescriber">
 <div class="dega">
   Ref.: <strong>{reference}</strong>
 </div>
 <div class="who">{prescriber_name}</div>
 {prescriber_sub}
 <div class="clear"></div>
</div>"""

    # --- 3. Patient information --------------------------------------------
    if patient:
        name_cell = _e(patient.first_name) + ' ' + _e(patient.last_name)
        age_sex_cell = f'{patient.age} y / {_e(patient.gender)}'
        dob_cell = (patient.date_of_birth.strftime('%d %b %Y')
                    if patient.date_of_birth else '&mdash;')
        phone_cell = _e(patient.phone) or '&mdash;'
        pid_cell = f'P-{patient.id:05d}'
    else:
        name_cell = age_sex_cell = dob_cell = phone_cell = pid_cell = '&mdash;'

    patient_block = ''
    if patient:
        address = _e(patient.address)
        if patient.city:
            address = (address + ', ' + _e(patient.city)) if address else _e(patient.city)
        if patient.country:
            address = (address + ', ' + _e(patient.country)) if address else _e(patient.country)
        patient_block = f"""
<table class="patient-table">
 <tr>
    <td class="k">Patient name</td><td class="v">{name_cell}</td>
    <td class="k">Age / Sex</td><td class="v">{age_sex_cell}</td>
    <td class="k">Patient ID</td><td class="v">{pid_cell}</td>
 </tr>
 <tr>
    <td class="k">Date of birth</td><td class="v">{dob_cell}</td>
    <td class="k">Contact</td><td class="v">{phone_cell}</td>
    <td class="k">Weight</td><td class="v">&mdash;</td>
 </tr>
 <tr>
    <td class="k">Address</td><td class="v" colspan="5">{address or '&mdash;'}</td>
 </tr>
</table>"""

    # --- 4. Date band (superscription context) ------------------------------
    # The month is spelled out in words rather than figures, and the diagnosis
    # sits beside the date, which is what makes the sheet auditable later.
    valid_cell = ''
    if prescription.valid_until:
        valid_cell = (
            '<div class="cell"><span class="k">Valid until</span>'
            f'<span class="v">{prescription.valid_until.strftime("%d %b %Y")}</span></div>'
        )
    meta_band = f"""
<div class="meta-band">
 <div class="cell"><span class="k">Date</span>
   <span class="v">{issued.strftime('%d %B %Y')}</span></div>
 <div class="cell"><span class="k">Diagnosis / indication</span>
   <span class="v">{_e(prescription.diagnosis) or '&mdash;'}</span></div>
 {valid_cell}
 <div class="cell right"><span class="k">Rx number</span>
   <span class="v">{reference}</span></div>
</div>"""

    allergy_block = ''
    if patient and patient.allergies:
        items = ''.join(
            f'<div class="alert"><strong>{_e(a.allergen)}</strong> '
            f'({_e(a.severity)}) &mdash; {_e(a.reaction)}</div>'
            for a in patient.allergies
        )
        allergy_block = f'<div class="section"><h3>Known allergies</h3>{items}</div>'

    rows, total_units, dispense_lines = _inscription_rows(prescription)

    # --- 6. Subscription (direction to the dispenser) ----------------------
    dispense_list = ''.join(f'<div>{line}</div>' for line in dispense_lines)
    subscription = f"""
<div class="subscription">
 <div class="head">Subscription &mdash; direction to the pharmacist</div>
 {dispense_list or '<div>Dispense as prescribed. Complete the full course.</div>'}
 <div style="margin-top:4px">Total units to dispense:
   <strong>{total_units or '&mdash;'}</strong></div>
</div>"""

    # --- 4. Superscription (the Rx symbol) ---------------------------------
    # Schedule H1 medicines carry extra dispensing duties, so the sheet flags
    # them next to the Rx symbol and repeats the statutory red-box warning.
    notified = _schedule_h1(medicines)
    h1_badge = ('<span class="flash" style="float:none">Schedule H1</span>'
                if notified else '')
    h1_block = ''
    if notified:
        h1_block = """
<div class="h1-box">
 <div class="t">Schedule H1 Drug &mdash; Warning</div>
 <div>It is dangerous to take this preparation except in accordance with the
   medical advice of a Registered Medical Practitioner.</div>
 <div>Not to be sold by retail without the prescription of a Registered Medical
   Practitioner. This supply has been entered in the Schedule H1 register.</div>
</div>"""
    rx_block = f"""
<div class="rx-line">
 <div class="rx">&#8478;<sup>&nbsp;{h1_badge}</sup></div>
 <div class="rx-meta">
    <div>Total items prescribed: <strong>{len(prescription.items)}</strong></div>
    <div>Duplicate retained by the pharmacy for <strong>3 years</strong></div>
 </div>
</div>"""

    conditions = ''
    if patient and patient.chronic_diseases:
        conditions = f"""
<div class="section">
 <h3>Chronic conditions</h3>
 <div class="notes">{_e(patient.chronic_diseases)}</div>
</div>"""

    other_meds = ''
    if patient and patient.current_medications:
        other_meds = f"""
<div class="section">
 <h3>Current medications</h3>
 <div class="notes">{_e(patient.current_medications)}</div>
</div>"""

    notes = ''
    if prescription.notes:
        notes = f"""
<div class="section">
 <h3>Advice / notes to the patient</h3>
 <div class="notes">{_e(prescription.notes)}</div>
</div>"""

    # --- 7. Sig. abbreviation legend ---------------------------------------
    legend = """
<div class="legend">
 <b>Sig. abbreviations used above</b>
 <div class="cols">
 <span>OD / o.d. &mdash; once daily</span>
 <span>BD / b.d. &mdash; twice daily</span>
 <span>TDS / t.d.s. &mdash; three times daily</span>
 <span>QID / q.i.d. &mdash; four times daily</span>
 <span>HS &mdash; at bedtime</span>
 <span>SOS &mdash; when required</span>
 <span>AC &mdash; before food</span>
 <span>PC &mdash; after food</span>
 <span>PO &mdash; by mouth</span>
 <span>1 tsf &mdash; one teaspoonful (5 ml)</span>
 </div>
</div>"""

    # --- 8. Renewal instructions -------------------------------------------
    renewal = """
<div class="renewal"><b>Renewal:</b> Refill not permitted unless expressly
 authorised by the prescriber and endorsed on this prescription.</div>"""

    # --- 9. Signatures and registration numbers ----------------------------
    # A prescription is only valid with the prescriber's signature and
    # registration number, so both lines are always printed.
    reg_line = _dotted(brand['prescriber_registration_no'])
    pharm_reg = _dotted(brand['pharmacist_registration_no'])
    sign_block = f"""
<div class="sign">
 <div>Dispensed by<br><br><br></div>
 <div>Prescriber signature &amp; date<br><br><br>
       <span style="font-size:10.5px">Reg. No.: {reg_line}</span></div>
</div>
<div style="margin-top:6px;font-size:10.5px;color:#4b5563">
 Registered pharmacist &mdash; Reg. No.: <strong>{pharm_reg}</strong>
 &nbsp;&bull;&nbsp; Pharmacy D.L. No.:
 <strong>{_dotted(brand['registration_no'])}</strong>
</div>"""

    body = f"""
<div class="sheet">
  {_header(brand, '')}
 {prescriber_block}
 {meta_band}

 {patient_block}

 {rx_block}

 <div class="section">
    <h3>Inscription &mdash; medicines prescribed</h3>
    <div class="inscription">
      <table>
        <thead>
          <tr><th style="width:26px">#</th><th style="width:27%">Medicine &amp; strength</th>
              <th style="width:30%">Sig. &mdash; direction to the patient</th>
              <th style="width:70px;text-align:center">Qty to dispense</th>
              <th style="width:22%">Route / schedule</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
 </div>

  {subscription}
  {renewal}
  {h1_block}

  {allergy_block}
  {conditions}
  {other_meds}
  {notes}

  {legend}
  {sign_block}
  {_footer(brand)}
</div>"""

    return Response(_page(f'Prescription #{prescription.id}', body), mimetype='text/html')


def _inscription_rows(prescription):
    """
    Build the inscription table rows for a prescription.

    Returns (rows_html, total_units, dispense_lines) where dispense_lines are the
    plain-text directions given to the pharmacist in the subscription.
    """
    rows = ''
    total_units = 0
    dispense_lines = []
    for index, item in enumerate(prescription.items, start=1):
        medicine = Medicine.query.get(item.medicine_id)
        composition = _e(medicine.salt_composition) if medicine else ''
        form = _e(medicine.form) if medicine else ''
        strength = _e(medicine.strength) if medicine else ''
        route = _e(medicine.route_of_administration) if medicine else ''
        schedule = _e(medicine.schedule_classification) if medicine else ''

        # Frequency per day, used to estimate the quantity to dispense.
        per_day = _frequency_per_day(item.frequency)
        name = _e(item.medicine.name if item.medicine else 'Unknown')
        # What is actually handed over: countable solid forms are dispensed in
        # their own name (tablets, capsules), everything else in its dose unit.
        dispense_unit = _dispense_unit(form, item.dosage_unit)
        if per_day:
            units = per_day * (item.duration_days or 0)
            total_units += units
            quantity = f'{units} {dispense_unit}'
            dispense_lines.append(
                f'{index}. {name} &mdash; dispense {units} '
                f'{dispense_unit} for {item.duration_days} day(s)'
            )
        else:
            quantity = f'{item.duration_days} day(s)'
            dispense_lines.append(
                f'{index}. {name} &mdash; dispense as directed '
                f'for {item.duration_days} day(s)'
            )

        # Sig.: the direction to the patient, written the way a prescriber
        # writes it - dose, then the Latin frequency abbreviation, then any
        # special direction - so it reads correctly to a pharmacist.
        dose_bit = f'{_format_num(item.dosage_amount)} {_e(item.dosage_unit)}'.strip()
        freq_bit = _sig_abbrev(item.frequency)
        sig_html = f'<span class="lat">{dose_bit}</span>'
        if freq_bit:
            sig_html += f' &mdash; <span class="lat">{freq_bit}</span>'
        if item.special_instructions:
            sig_html += ' &mdash; ' + _e(item.special_instructions).rstrip('.')

        # The generic name is what identifies the medicine clinically.
        generic = _e(medicine.generic_name) if medicine else ''
        # The medicine name usually already embeds the strength ('Amoxicillin
        # 500mg'), so repeating it from the strength field prints a duplicate.
        # Only add the strength when the name does not already carry it.
        name_text = (medicine.name if medicine else '') or ''
        strength_bits = [b for b in (strength or '').split() if b]
        name_has_strength = all(b.lower() in name_text.lower()
                                for b in strength_bits) if strength_bits else False
        detail = form if name_has_strength else ' '.join(filter(None, [strength, form]))
        meta_bits = []
        if route:
            meta_bits.append('Route: ' + route)
        if schedule:
            sched_txt = schedule
            if 'h1' in schedule.lower().replace(' ', '').replace('-', ''):
                sched_txt = (f'<span style="color:#b91c1c;font-weight:700">'
                             f'{schedule}</span>')
            meta_bits.append('Schedule: ' + sched_txt)
        meta = '<br>'.join(
            f'<span style="color:#6b7280;font-size:10.5px">{bit}</span>'
            for bit in meta_bits
        )

        name_line = f'<strong>{name}</strong>'
        if detail:
            name_line += f' <span style="font-weight:400">{detail}</span>'
        # The generic name identifies the medicine clinically, so it is cited
        # under the brand name the way a pharmacopoeial monograph would cite it.
        # Suppressed when the two are effectively the same string (a generic-only
        # catalogue entry), which would otherwise print the name twice.
        def _same(a, b):
            strip = lambda s: ''.join(c for c in s.lower() if c.isalnum())
            return not a or strip(a) == strip(b)
        if generic and medicine and not _same(generic, medicine.name):
            comp_line = (f'<br><span style="color:#6b7280;font-size:10.5px">'
                         f'{generic}</span>')
        elif composition:
            comp_line = (f'<br><span style="color:#6b7280;font-size:10.5px">'
                         f'{composition}</span>')
        else:
            comp_line = ''

        rows += f"""
      <tr>
        <td class="rx-num">{index}</td>
        <td>{name_line}{comp_line}</td>
        <td class="sig">{sig_html}</td>
        <td style="text-align:center">{quantity}</td>
        <td>{meta or '&mdash;'}</td>
      </tr>"""

    return rows, total_units, dispense_lines


def _format_num(value):
    """Render a dose number without a trailing '.0'."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _e(value)
    if number == int(number):
        return str(int(number))
    return str(number)


def _dispense_unit(form, dose_unit):
    # The unit a medicine is physically dispensed in.
    #
    # A tablet or capsule is counted in tablets/capsules, not in its milligram
    # strength, so a 7-day course of one tablet daily dispenses '7 tablets' -
    # not '7 mg'. Liquid, topical and inhaled forms keep their stated dose unit
    # (ml, g, puffs), because that is what is measured out.
    countable = {
        'tablet': 'tablets', 'tab': 'tablets', 'caplet': 'caplets',
        'capsule': 'capsules', 'cap': 'capsules', 'pill': 'pills',
        'sachet': 'sachets', 'suppository': 'suppositories',
        'lozenge': 'lozenges', 'patch': 'patches',
        'drops': 'drops', 'drop': 'drops', 'puff': 'puffs',
    }
    key = (form or '').strip().lower()
    if key in countable:
        return countable[key]
    # 'tablet' may be embedded, e.g. 'film-coated tablet'.
    for word, plural in countable.items():
        if word in key:
            return plural
    return _e(dose_unit) or 'unit'


def _frequency_per_day(frequency):
    """
    Number of doses per day for a free-text frequency, or None when it cannot be
    determined. Handles both worded ('3 times a day') and abbreviated ('TDS')
    forms.
    """
    if not frequency:
        return None
    import re
    text = str(frequency).strip().lower()
    for token in ('once', 'one time'):
        if token in text:
            return 1
    for token in ('twice', 'two times'):
        if token in text:
            return 2
    for word, count in (('thrice', 3), ('three', 3), ('four', 4)):
        if word in text:
            return count
    abbreviations = {
        'qid': 4, 'q.d.s': 4, 'qds': 4, 'bds': 2, 'bd': 2, 'b.d': 2, 'bid': 2,
        'tds': 3, 't.d.s': 3, 'tid': 3, 'od': 1, 'o.d': 1, 'hs': 1, 'nocte': 1,
        'sos': 1,
    }
    for token, count in abbreviations.items():
        if token in text.split() or token in text:
            return count
    # Numeric forms such as '3 times a day' or '2-3 times daily'.
    match = re.search(r'(\d+)\s*(?:times|doses|x|/day)', text)
    if match:
        return int(match.group(1))
    return None


def _sig_text(frequency):
    """Expand a stored frequency into a readable, standardised Sig. phrase."""
    if not frequency:
        return ''
    text = str(frequency).strip()
    mapping = {
        'OD': 'once daily', 'O.D': 'once daily', 'BD': 'twice daily',
        'B.D': 'twice daily', 'BID': 'twice daily', 'TDS': 'three times daily',
        'T.D.S': 'three times daily', 'TID': 'three times daily',
        'QID': 'four times daily', 'Q.I.D': 'four times daily',
        'HS': 'at bedtime', 'SOS': 'when required',
    }
    return mapping.get(text.upper(), text.lower())


def _sig_abbrev(frequency):
    # Render a stored frequency as the Latin abbreviation a prescription uses.
    #
    # Prescriptions are traditionally written in the classical Latin shorthand -
    # b.d., t.d.s., q.i.d. - because that is what a pharmacist reads fastest and
    # what the pharmacopoeial examples show. Recognised wordings are converted
    # to that form; anything unrecognised is passed through unchanged rather
    # than being guessed at.
    if not frequency:
        return ''
    text = str(frequency).strip()
    upper = text.upper().replace('.', '').replace(' ', '')

    exact = {
        'OD': 'o.d.', 'QD': 'o.d.', 'ONCEDAILY': 'o.d.', 'ONETIMEADAY': 'o.d.',
        'BD': 'b.d.', 'BID': 'b.d.', 'BDS': 'b.d.', 'TWICEDAILY': 'b.d.',
        'TWOTIMESADAY': 'b.d.',
        'TDS': 't.d.s.', 'TID': 't.d.s.', 'THRICEDAILY': 't.d.s.',
        'THREETIMESADAY': 't.d.s.',
        'QID': 'q.i.d.', 'QDS': 'q.i.d.', 'FOURTIMESADAY': 'q.i.d.',
        'HS': 'h.s.', 'NOCTE': 'nocte',
        'SOS': 's.o.s.', 'PRN': 'p.r.n.',
    }
    if upper in exact:
        return exact[upper]

    # Wordier phrasings such as '3 times a day' or 'every 8 hours'.
    word_map = [
        ('once', 'o.d.'), ('one time', 'o.d.'),
        ('twice', 'b.d.'), ('two times', 'b.d.'),
        ('thrice', 't.d.s.'), ('three times', 't.d.s.'),
        ('four times', 'q.i.d.'),
    ]
    lowered = text.lower()
    for token, abbrev in word_map:
        if token in lowered:
            return abbrev
    # Numeric forms: '3 times a day' -> t.d.s., 'every 8 hours' -> q.8.h.
    import re
    times = re.search(r'\b(\d+)\s*(?:times|doses|tds)\b', lowered)
    if times:
        count = int(times.group(1))
        return {1: 'o.d.', 2: 'b.d.', 3: 't.d.s.', 4: 'q.i.d.'}.get(count, text)

    hours = re.search(r'every\s*(\d+)\s*(?:h|hr|hrs|hour|hours)\b', lowered)
    if hours:
        abbrev = 'q.%s.h.' % hours.group(1)
        # 'every 8 hours as needed' also carries a p.r.n. (when required) note.
        if 'as needed' in lowered or 'when required' in lowered or 'if needed' in lowered:
            abbrev += ' p.r.n.'
        return abbrev
    # p.r.n. alone: 'as needed' / 'when required'.
    if any(t in lowered for t in ('as needed', 'when required', 'if needed')):
        return 'p.r.n.'
    return text


def patient_report(patient_id):
    """
    Full patient history: demographics, allergies, conditions and every
    prescription on record, under the pharmacy letterhead.
    """
    patient = Patient.query.get_or_404(patient_id)
    brand = _brand_header()

    prescriptions = (Prescription.query
                     .filter_by(patient_id=patient_id)
                     .order_by(Prescription.created_at.desc())
                     .all())

    allergies = ''
    if patient.allergies:
        allergies = ''.join(
            f'<div class="alert"><strong>{_e(a.allergen)}</strong> '
            f'({_e(a.severity)}) &mdash; {_e(a.reaction)}</div>'
            for a in patient.allergies
        )
    else:
        allergies = '<div class="ok">No allergies recorded.</div>'

    history = ''
    if not prescriptions:
        history = '<div class="notes">No prescriptions recorded for this patient.</div>'
    for prescription in prescriptions:
        rows = ''
        for item in prescription.items:
            medicine = Medicine.query.get(item.medicine_id)
            rows += f"""
          <tr>
            <td><strong>{_e(item.medicine.name if item.medicine else 'Unknown')}</strong>
                <br><span style="color:#6b7280;font-size:11px">
                {_e(medicine.salt_composition) if medicine else ''}</span></td>
            <td>{_e(item.dosage_amount)} {_e(item.dosage_unit)}</td>
            <td>{_e(item.frequency)}</td>
            <td>{_e(item.duration_days)} days</td>
          </tr>"""
        history += f"""
<div class="section">
 <h3>{prescription.created_at.strftime('%d %b %Y')} &mdash; {_e(prescription.diagnosis)}</h3>
 <div class="grid" style="margin-bottom:6px">
    <div><div class="label">Prescriber</div>
         <div class="value">{_e(prescription.doctor_name)}</div></div>
    <div><div class="label">Record no.</div>
         <div class="value">Rx #{prescription.id}</div></div>
 </div>
 <table>
    <thead><tr><th style="width:40%">Medicine</th><th>Dose</th>
               <th>Frequency</th><th>Duration</th></tr></thead>
    <tbody>{rows}</tbody>
 </table>
  {f'<div class="notes" style="margin-top:6px">{_e(prescription.notes)}</div>' if prescription.notes else ''}
</div>"""

    body = f"""
<div class="sheet">
  {_header(brand, 'Patient Record')}
 <div class="grid">
    <div><div class="label">Patient</div>
         <div class="value">{_e(patient.first_name)} {_e(patient.last_name)}</div></div>
    <div><div class="label">Age / Sex</div>
         <div class="value">{patient.age} yrs / {_e(patient.gender)}</div></div>
    <div><div class="label">Date of birth</div>
         <div class="value">{patient.date_of_birth.strftime('%d %b %Y') if patient.date_of_birth else '&mdash;'}</div></div>
    <div><div class="label">Record no.</div><div class="value">#{patient.id}</div></div>
    <div><div class="label">Phone</div><div class="value">{_e(patient.phone) or '&mdash;'}</div></div>
    <div><div class="label">Email</div><div class="value">{_e(patient.email) or '&mdash;'}</div></div>
    <div><div class="label">Address</div>
         <div class="value">{_e(patient.address) or '&mdash;'}{', ' + _e(patient.city) if patient.city else ''}</div></div>
    <div><div class="label">Total visits</div>
         <div class="value">{len(prescriptions)}</div></div>
 </div>

 <div class="section">
    <h3>Allergies</h3>
    {allergies}
 </div>

 <div class="section">
    <h3>Chronic conditions</h3>
    <div class="notes">{_e(patient.chronic_diseases) or 'None recorded.'}</div>
 </div>

 <div class="section">
    <h3>Current medications</h3>
    <div class="notes">{_e(patient.current_medications) or 'None recorded.'}</div>
 </div>

 <div class="section">
    <h3>Prescription history</h3>
    {history}
 </div>

 <div class="sign">
    <div>Patient / attendant</div>
    <div>Pharmacist signature &amp; seal</div>
 </div>
  {_footer(brand)}
</div>"""

    return Response(
        _page(f'{patient.first_name} {patient.last_name} - Patient Record', body),
        mimetype='text/html',
    )


@report_bp.route('/inventory', methods=['GET'])
def inventory_report():
    """Printable stock position, useful for a physical stock take."""
    from app.models import Inventory

    brand = _brand_header()
    rows = ''
    for item in Inventory.query.all():
        status = item.status.replace('_', ' ')
        rows += f"""
      <tr>
        <td><strong>{_e(item.medicine.name if item.medicine else '')}</strong></td>
        <td>{_e(item.batch_number)}</td>
        <td style="text-align:right">{item.quantity_in_stock}</td>
        <td style="text-align:right">{item.reorder_level}</td>
        <td>{_e(item.expiry_date.strftime('%d %b %Y') if item.expiry_date else '')}</td>
        <td>{_e(item.storage_location)}</td>
        <td>{_e(status)}</td>
      </tr>"""

    body = f"""
<div class="sheet">
  {_header(brand, 'Stock Position')}
 <div class="section">
    <table>
      <thead>
        <tr><th style="width:30%">Medicine</th><th>Batch</th>
            <th style="text-align:right">Qty</th>
            <th style="text-align:right">Reorder at</th>
            <th>Expiry</th><th>Location</th><th>Status</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
 </div>
  {_footer(brand)}
</div>"""

    return Response(_page('Stock position', body), mimetype='text/html')
