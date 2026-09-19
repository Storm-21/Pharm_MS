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
    }


BASE_CSS = """
  @page { size: A4; margin: 14mm; }
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #111827; margin: 0; padding: 24px; background: #f3f4f6;
    font-size: 13px; line-height: 1.45;
  }
  .sheet {
    max-width: 210mm; margin: 0 auto; background: #fff; padding: 14mm;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
  }
  .head { display: flex; gap: 18px; align-items: flex-start;
          border-bottom: 3px solid #2563eb; padding-bottom: 14px; }
  .head img { width: 74px; height: 74px; object-fit: contain; flex: 0 0 auto; }
  .head .titles { flex: 1; min-width: 0; }
  .head h1 { margin: 0 0 4px; font-size: 25px; color: #1e3a8a; letter-spacing: .2px; }
  .head .contact { color: #4b5563; font-size: 11.5px; }
  .head .pharmacist { color: #374151; font-size: 11.5px; margin-top: 3px; }
  .doc-title { margin: 16px 0 10px; font-size: 15px; font-weight: 700;
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
  .sign { margin-top: 40px; display: flex; justify-content: space-between; }
  .sign div { border-top: 1px solid #9ca3af; padding-top: 5px;
              width: 200px; font-size: 11.5px; color: #4b5563; text-align: center; }
  .foot { margin-top: 22px; border-top: 1px solid #e5e7eb; padding-top: 9px;
          color: #6b7280; font-size: 10.5px; text-align: center; }
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
    .toolbar { display: none; }
    tr:nth-child(even) td { background: transparent; }
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
    return f"""
<div class="head">
 <img src="{brand['logo_url']}" alt="Logo">
 <div class="titles">
    <h1>{brand['name']}</h1>
    <div class="contact">{brand['contact']}</div>
    {pharmacist}
 </div>
</div>
<div class="doc-title">{_e(doc_title)}</div>"""


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

    allergy_block = ''
    if patient and patient.allergies:
        items = ''.join(
            f'<div class="alert"><strong>{_e(a.allergen)}</strong> '
            f'({_e(a.severity)}) &mdash; {_e(a.reaction)}</div>'
            for a in patient.allergies
        )
        allergy_block = f'<div class="section"><h3>Known allergies</h3>{items}</div>'

    rows = ''
    for item in prescription.items:
        medicine = Medicine.query.get(item.medicine_id)
        composition = _e(medicine.salt_composition) if medicine else ''
        rows += f"""
      <tr>
        <td>
          <strong>{_e(item.medicine.name if item.medicine else 'Unknown')}</strong><br>
          <span style="color:#6b7280;font-size:11px">{composition}</span>
        </td>
        <td>{_e(item.dosage_amount)} {_e(item.dosage_unit)}</td>
        <td>{_e(item.frequency)}</td>
        <td>{_e(item.duration_days)} days</td>
        <td>{_e(item.special_instructions)}</td>
      </tr>"""

    patient_block = ''
    if patient:
        patient_block = f"""
<div class="grid">
 <div><div class="label">Patient</div>
       <div class="value">{_e(patient.first_name)} {_e(patient.last_name)}</div></div>
 <div><div class="label">Age / Sex</div>
       <div class="value">{patient.age} yrs / {_e(patient.gender)}</div></div>
 <div><div class="label">Phone</div><div class="value">{_e(patient.phone) or '&mdash;'}</div></div>
 <div><div class="label">Record no.</div><div class="value">#{patient.id}</div></div>
</div>"""

    conditions = ''
    if patient and patient.chronic_diseases:
        conditions = f"""
<div class="section">
 <h3>Chronic conditions</h3>
 <div class="notes">{_e(patient.chronic_diseases)}</div>
</div>"""

    notes = ''
    if prescription.notes:
        notes = f"""
<div class="section">
 <h3>Notes</h3>
 <div class="notes">{_e(prescription.notes)}</div>
</div>"""

    valid = ''
    if prescription.valid_until:
        valid = (f'<div><div class="label">Valid until</div>'
                 f'<div class="value">{prescription.valid_until.strftime("%d %b %Y")}</div></div>')

    body = f"""
<div class="sheet">
  {_header(brand, 'Prescription')}
  {patient_block}
 <div class="grid">
    <div><div class="label">Diagnosis</div>
         <div class="value">{_e(prescription.diagnosis)}</div></div>
    <div><div class="label">Prescribed by</div>
         <div class="value">{_e(prescription.doctor_name)}</div></div>
    <div><div class="label">Date</div>
         <div class="value">{prescription.created_at.strftime('%d %b %Y')}</div></div>
    {valid}
 </div>

 <div class="section">
    <h3>Medicines prescribed</h3>
    <table>
      <thead>
        <tr><th style="width:32%">Medicine</th><th>Dose</th>
            <th>Frequency</th><th>Duration</th><th>Instructions</th></tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
 </div>

  {allergy_block}
  {conditions}
  {notes}

 <div class="sign">
    <div>Dispensed by</div>
    <div>Pharmacist signature &amp; seal</div>
 </div>
  {_footer(brand)}
</div>"""

    return Response(_page(f'Prescription #{prescription.id}', body), mimetype='text/html')


@report_bp.route('/patient/<int:patient_id>', methods=['GET'])
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
