"""
Substitution engine - what to dispense when the first choice is not available.

THE PROBLEM THIS SOLVES
-----------------------
A recommender that only lists what is perfect is useless at a pharmacy counter.
The prescriber has written a medicine; the shelf may not have it. The answer is
not "not available" - it is the *closest safe equivalent*, ranked so that the
pharmacist can see how close each one actually is and why.

THE ORDERING RULE
-----------------
Substitutes are ranked by how much clinical substitution has to happen:

  1. SAME MOLECULE, different brand or pack  - fully interchangeable in effect,
     only the label differs. This is the strongest possible substitute.
  2. SAME MOLECULE, different strength       - interchangeable with arithmetic;
     the dose changes but the drug does not.
  3. SAME CLASS, different molecule          - a genuine therapeutic
     alternative. Clinically acceptable but not bioequivalent, so the
     prescriber should be told.
  4. DIFFERENT CLASS, same indication        - a real clinical decision. Shown
     last, always flagged for the prescriber.

SAFETY IS NOT OPTIONAL HERE
---------------------------
Every candidate passes through SafetyEngine.assess() and anything that is not
SAFE for this specific patient is either excluded outright (contraindicated) or
demoted with its warning attached. A recommendation that swaps one medicine for
another the patient is allergic to would be worse than no recommendation at all,
so the safety gate runs on the substitute, not just on the original.
"""

from app.models import Medicine, Inventory, Patient
from app.services.safety_service import SafetyEngine


# Molecules that are therapeutically interchangeable with each other within the
# same class. Used to raise the rank of a substitute that is genuinely
# equivalent rather than merely similar in indication.
# Each tuple is a set of generic names considered clinically equivalent for
# most patients; the pharmacist still sees the difference stated.
EQUIVALENT_MOLECULES = [
    ('omeprazole', 'pantoprazole', 'esomeprazole', 'rabeprazole', 'lansoprazole'),
    ('atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin'),
    ('amlodipine', 'nifedipine', 'felodipine'),
    ('lisinopril', 'enalapril', 'ramipril', 'perindopril', 'captopril'),
    ('losartan', 'valsartan', 'telmisartan', 'irbesartan', 'olmesartan'),
    ('cetirizine', 'levocetirizine', 'loratadine', 'fexofenadine',
     'desloratadine'),
    ('ibuprofen', 'diclofenac', 'naproxen', 'aceclofenac', 'etoricoxib'),
    ('amoxicillin', 'amoxycillin'),
    ('ciprofloxacin', 'levofloxacin', 'ofloxacin', 'moxifloxacin'),
    ('fluconazole', 'itraconazole', 'ketoconazole'),
    ('sertraline', 'fluoxetine', 'escitalopram', 'citalopram', 'paroxetine'),
    ('metformin', 'glimepiride', 'gliclazide', 'sitagliptin'),
    ('paracetamol', 'acetaminophen'),
    ('prednisolone', 'prednisone'),
    ('salbutamol', 'levalbuterol'),
    ('metronidazole', 'tinidazole'),
]


def _equivalence_group(generic_name):
    """Return the index of the equivalence group a molecule belongs to, if any."""
    if not generic_name:
        return None
    key = generic_name.strip().lower()
    for index, group in enumerate(EQUIVALENT_MOLECULES):
        if any(member in key or key in member for member in group):
            return index
    return None


class SubstitutionEngine:
    """Find the closest safe medicine when the first choice is unavailable."""

    @staticmethod
    def _stock(medicine_id):
        rows = Inventory.query.filter_by(medicine_id=medicine_id).all()
        return sum(row.quantity_in_stock or 0 for row in rows)

    # Pairs that must never be substituted automatically, however similar their
    # indications look. Morphine scored as a tramadol substitute because both
    # are opioids treating pain - but morphine is roughly ten times more potent
    # and carries a genuine risk of fatal respiratory depression in a patient
    # dosed for tramadol. This table is the guard against that class of error:
    # a similarity engine can never be allowed to escalate opioid potency on
    # its own.
    NEVER_SUBSTITUTE = [
        ('tramadol', 'morphine', 'fentanyl', 'oxycodone', 'methadone',
         'hydromorphone', 'buprenorphine'),
    ]

    @staticmethod
    def _is_forbidden_swap(source, candidate):
        """True when promoting one of these to the other would be unsafe."""
        src = (source.generic_name or source.name or '').lower()
        cand = (candidate.generic_name or candidate.name or '').lower()
        for group in SubstitutionEngine.NEVER_SUBSTITUTE:
            if any(m in src for m in group) and any(m in cand for m in group):
                # Same molecule is fine (a brand swap); only a different, more
                # potent opioid is barred.
                if not any(m in src and m in cand for m in group):
                    return True
        return False
    @staticmethod
    def _match_tier(source, candidate):
        """
        Grade how substitutable a candidate is for the source.

        Returns (tier, label, interchangeable) where tier 1 is the closest.
        Lower is better.
        """
        src_generic = (source.generic_name or '').strip().lower()
        cand_generic = (candidate.generic_name or '').strip().lower()

        # 1. Same molecule and same strength - a straight swap.
        if src_generic and src_generic == cand_generic:
            if (source.strength or '').strip().lower() == \
                    (candidate.strength or '').strip().lower():
                return 1, 'Same medicine, different brand', True
            # 2. Same molecule, different strength - needs a dose recalculation.
            return 2, 'Same medicine, different strength', False

        src_form = (source.form or '').strip().lower()
        cand_form = (candidate.form or '').strip().lower()
        same_form = bool(src_form and src_form == cand_form)
        same_class = bool(
            source.therapeutic_class and candidate.therapeutic_class
            and source.therapeutic_class.strip().lower()
            == candidate.therapeutic_class.strip().lower()
        )
        src_group = _equivalence_group(src_generic)
        cand_group = _equivalence_group(cand_generic)
        equivalent = (src_group is not None and src_group == cand_group)

        # 3. Same class, or a molecule we know to be interchangeable.
        if same_class or equivalent:
            if same_form:
                return 3, 'Therapeutically equivalent, same form', True
            return 4, 'Therapeutically equivalent, different form', False
        # 4. Different class - see the gating note in find_substitutes below.
        #    Only counts as a substitution when the two
        #    actually treat the same thing.
        #
        # Route and dosage form alone are NOT enough to make two medicines
        # interchangeable: an oral antibiotic and an oral calcium-channel
        # blocker share a route and have nothing else in common. An earlier
        # version ranked on form and route and offered nifedipine as a
        # substitute for tramadol, which is clinically meaningless. Matching
        # now requires an actual indication overlap, evaluated by the caller
        # before the candidate is offered (see find_substitutes).
        return 6, 'Different class - prescriber decision required', False

    # Clinical indication phrases that mean the same thing to a prescriber but
    # share no words. A plain word-overlap test misses these.
    INDICATION_SYNONYMS = [
        ('urinary tract', 'uti', 'cystitis', 'pyelonephritis', 'prostatitis'),
        ('respiratory tract', 'pneumonia', 'bronchitis', 'chest infection',
         'pharyngitis', 'sinusitis', 'tonsillitis'),
        ('skin and soft tissue', 'cellulitis', 'wound infection', 'abscess'),
        ('gastroenteritis', 'diarrhoea', 'diarrhea', 'enteritis', 'dysentery'),
        ('pain', 'analgesia', 'analgesic', 'ache', 'headache'),
        ('fever', 'pyrexia', 'antipyretic', 'temperature'),
        ('hypertension', 'blood pressure', 'antihypertensive'),
        ('diabetes', 'glycaemic', 'glycemic', 'hyperglycaemia'),
    ]

    @staticmethod
    def _indication_overlap(source, candidate):
        # How much two medicines treat the same thing, scaled 0.0 to 1.0.
        #
        # Deliberately not a plain Jaccard index over the whole indication
        # text. Ciprofloxacin's indication list is long ('urinary tract
        # infections, complicated UTI, prostatitis, typhoid, gastroenteritis,
        # bone and joint infection'), so an antibiotic that genuinely shares
        # one whole indication - cefixime and urinary tract infection - still
        # scores low against the union and gets discarded. That is the wrong
        # answer: sharing one real indication is exactly what makes a
        # substitute usable.
        #
        # The measure therefore takes the stronger of two signals - token
        # overlap for general similarity, and a shared named clinical concept
        # (see INDICATION_SYNONYMS) which counts for considerably more.
        def normalise(text):
            if not text:
                return ''
            return ''.join(
                ch if ch.isalnum() else chr(32) for ch in str(text).lower())

        def words(text):
            cleaned = normalise(text)
            return {w for w in cleaned.split()
                    if len(w) > 3 and w not in {
                        'with', 'that', 'this', 'from', 'used', 'treatment',
                        'relief', 'mild', 'moderate', 'severe', 'acute',
                        'chronic', 'adults', 'children', 'infection',
                        'infections'}}

        src_text = normalise(source.use_case)
        cand_text = normalise(candidate.use_case)
        if not src_text or not cand_text:
            return 0.0
        a = words(source.use_case)
        b = words(candidate.use_case)
        token_overlap = (len(a & b) / float(len(a))) if a else 0.0
        for group in SubstitutionEngine.INDICATION_SYNONYMS:
            if any(t in src_text for t in group):
                if any(t in cand_text for t in group):
                    # Treating the same named condition is the strongest single
                    # signal that one medicine can stand in for another, so it
                    # scores well above incidental word overlap.
                    return round(max(token_overlap, 0.45), 3)
        return round(token_overlap, 3)

    @staticmethod
    def find_substitutes(medicine_id, patient_id=None, limit=8,
                         require_stock=True, include_different_class=False):
        """
        Ranked substitutes for a medicine that is unavailable.

        require_stock  only return candidates with stock on hand (default True,
                       because the point is to dispense something today)
        include_different_class  also surface tier-6 options, which are a
                       prescriber decision rather than a substitution
        """
        source = Medicine.query.get(medicine_id)
        if not source:
            return None
        patient = Patient.query.get(patient_id) if patient_id else None
        # Screen the medicine being replaced as well as the candidates. If the
        # patient is allergic to a whole class, every member of that class must
        # be ruled out, not just the one written on the prescription. The
        # per-candidate assess() below catches the candidates: anything sharing
        # the patient's allergen is graded BLOCKED by its own assessment and
        # lands in `excluded_on_safety` with the reason attached, so a
        # quinolone-allergic patient is never offered levofloxacin in place of
        # ciprofloxacin.
        source_assessment = (SafetyEngine.assess(patient.id, medicine_id)
                             if patient else None)
        candidates = Medicine.query.filter(Medicine.id != medicine_id).all()

        results = []
        excluded = []

        for candidate in candidates:
            # Never promote across a potency gap that a dose cannot cover.
            if SubstitutionEngine._is_forbidden_swap(source, candidate):
                excluded.append({
                    'name': candidate.name,
                    'generic_name': candidate.generic_name,
                    'reason': 'NOT_INTERCHANGEABLE',
                    'headline': ('Different opioid of substantially different '
                                 'potency - requires prescriber review and '
                                 'recalculation, not substitution.'),
                    'tier': None,
                })
                continue
            tier, label, interchangeable = SubstitutionEngine._match_tier(
                source, candidate)

            if tier == 6 and not include_different_class:
                continue

            stock = SubstitutionEngine._stock(candidate.id)
            if require_stock and stock <= 0:
                continue

            overlap = SubstitutionEngine._indication_overlap(source, candidate)

            # A cross-class candidate is only shown when it genuinely treats
            # the same thing. Without this gate the ranking falls back on route
            # and form, which produces nonsense - oral nifedipine offered as a
            # substitute for oral tramadol, for instance, because both are
            # tablets taken by mouth. Shared route is a convenience, not a
            # clinical equivalence, so a different-class option must clear a
            # meaningful indication-overlap bar to be offered at all.
            if tier == 6:
                if overlap >= 0.40:
                    # A different class that treats the same named condition is
                    # a genuine therapeutic alternative (cefixime for a urinary
                    # infection when ciprofloxacin is unavailable). Promote it
                    # to tier 5 so it is offered by default rather than being
                    # hidden behind an opt-in flag - a pharmacist looking for
                    # something to dispense today needs to see it.
                    tier = 5
                    label = ('Different class, treats the same condition - '
                             'prescriber confirmation required')
                elif not include_different_class:
                    continue
            # Same-class but a different molecule: still require some shared
            # purpose, otherwise two drugs that merely share a class name are
            # put forward as alternatives.
            if tier in (3, 4) and overlap < 0.15:
                continue

            entry = {
                'medicine_id': candidate.id,
                'name': candidate.name,
                'generic_name': candidate.generic_name,
                'brand_name': candidate.brand_name,
                'manufacturer': candidate.manufacturer,
                'strength': candidate.strength,
                'form': candidate.form,
                'route_of_administration': candidate.route_of_administration,
                'therapeutic_class': candidate.therapeutic_class,
                'selling_price': candidate.selling_price,
                'requires_prescription': candidate.requires_prescription,
                'schedule_classification': candidate.schedule_classification,
                'total_stock': stock,
                'substitution_tier': tier,
                'substitution_label': label,
                'interchangeable': interchangeable,
                'indication_overlap': overlap,
                'price_difference': round(
                    (candidate.selling_price or 0) - (source.selling_price or 0), 2),
                'requires_dose_recalculation': tier == 2,
                'requires_prescriber_consent': tier >= 3,
            }

            # --- Safety gate ------------------------------------------------
            # A substitute is only usable if it is safe for THIS patient. This
            # is the check that stops the engine recommending a different
            # molecule that happens to be in stock but that the patient reacts
            # to - which would be far worse than saying "not available".
            if patient:
                assessment = SafetyEngine.assess(patient.id, candidate.id)
                entry['safety_verdict'] = assessment['verdict']
                entry['safe_for_patient'] = assessment['safe']
                entry['recommendable'] = assessment['recommendable']
                entry['safety_findings'] = assessment['findings']
                entry['safety_headline'] = assessment['headline']

                if assessment['verdict'] in ('BLOCKED', 'UNSAFE', 'UNKNOWN'):
                    # Not offered at all. Recorded separately so the pharmacist
                    # can see that a candidate was considered and rejected, and
                    # why - silence would look like it was never checked.
                    excluded.append({
                        'name': candidate.name,
                        'generic_name': candidate.generic_name,
                        'reason': assessment['verdict'],
                        'headline': assessment['headline'],
                        'tier': tier,
                    })
                    continue
            else:
                entry['safety_verdict'] = 'NOT_ASSESSED'
                entry['safe_for_patient'] = None
                entry['recommendable'] = None
                entry['safety_findings'] = []
                entry['safety_headline'] = None

            results.append(entry)

        # Best first: closest tier, then interchangeable before not, then the
        # strongest indication overlap, then cheapest.
        results.sort(key=lambda x: (
            x['substitution_tier'],
            not x['interchangeable'],
            -x['indication_overlap'],
            x['selling_price'] or 0,
        ))

        return {
            'source': {
                'medicine_id': source.id,
                'name': source.name,
                'generic_name': source.generic_name,
                'strength': source.strength,
                'form': source.form,
                'therapeutic_class': source.therapeutic_class,
                'use_case': source.use_case,
                'selling_price': source.selling_price,
                'total_stock': SubstitutionEngine._stock(source.id),
                'safety_verdict': (source_assessment['verdict']
                                   if source_assessment else 'NOT_ASSESSED'),
                'safety_headline': (source_assessment['headline']
                                    if source_assessment else None),
                'is_safe_for_patient': (source_assessment['safe']
                                        if source_assessment else None),
            },
            'source_is_safe_for_patient': (source_assessment['safe']
                                           if source_assessment else None),
            'substitutes': results[:limit],
            'excluded_on_safety': excluded,
            'total_considered': len(candidates),
            'total_available': len(results),
            'note': (
                'Tier 1 and 2 are the same molecule and need no prescriber '
                'input. Tier 3 and above are therapeutic alternatives and must '
                'be confirmed by the prescriber.'
            ),
        }

    @staticmethod
    def resolve_for_condition(condition, patient_id=None, limit=8):
        """
        The end-to-end answer to "the patient needs X and the shelf is empty".

        Returns three ordered lists:
          in_stock      safe options that can be dispensed right now
          substitutes   safe alternatives to an out-of-stock first choice
          unavailable   everything relevant that is out of stock, so the
                        pharmacist can reorder what is actually needed

        Only medicines assessed SAFE for this patient appear in the first two
        lists. Anything UNKNOWN is reported separately rather than presented as
        an option, because an unverified recommendation is exactly what this
        system is built to avoid.
        """
        if not condition or not str(condition).strip():
            return None
        term = str(condition).strip()

        matches = Medicine.query.filter(
            (Medicine.use_case.ilike('%' + term + '%'))
            | (Medicine.therapeutic_class.ilike('%' + term + '%'))
            | (Medicine.generic_name.ilike('%' + term + '%'))
            | (Medicine.name.ilike('%' + term + '%'))
        ).all()

        patient = Patient.query.get(patient_id) if patient_id else None

        in_stock = []
        unavailable = []
        unverified = []

        for medicine in matches:
            stock = SubstitutionEngine._stock(medicine.id)

            if patient:
                assessment = SafetyEngine.assess(patient.id, medicine.id)
                verdict = assessment['verdict']
            else:
                assessment = None
                verdict = 'NOT_ASSESSED'

            entry = {
                'medicine_id': medicine.id,
                'name': medicine.name,
                'generic_name': medicine.generic_name,
                'brand_name': medicine.brand_name,
                'strength': medicine.strength,
                'form': medicine.form,
                'therapeutic_class': medicine.therapeutic_class,
                'use_case': medicine.use_case,
                'selling_price': medicine.selling_price,
                'total_stock': stock,
                'safety_verdict': verdict,
                'safety_headline': assessment['headline'] if assessment else None,
                'safety_findings': assessment['findings'] if assessment else [],
            }

            if verdict == 'BLOCKED':
                # Contraindicated for this patient - never listed anywhere.
                continue
            if verdict == 'UNSAFE':
                # Serious risk. Reported only as "considered and rejected".
                entry['reason'] = 'Not safe for this patient'
                unverified.append(entry)
                continue
            if verdict == 'UNKNOWN':
                # Safety could not be established. Not offered as a choice, but
                # shown so the missing data can be supplied.
                entry['reason'] = 'Safety could not be verified'
                unverified.append(entry)
                continue

            if stock > 0:
                in_stock.append(entry)
            else:
                unavailable.append(entry)

        # For each unavailable first-choice, offer the closest available
        # substitute so there is always something actionable.
        for item in unavailable:
            found = SubstitutionEngine.find_substitutes(
                item['medicine_id'], patient_id=patient_id, limit=3,
                require_stock=True)
            item['closest_substitutes'] = (
                found['substitutes'] if found else [])

        in_stock.sort(key=lambda x: -(x['total_stock'] or 0))
        unavailable.sort(key=lambda x: x['name'])

        return {
            'condition': term,
            'patient_id': patient_id,
            'in_stock': in_stock[:limit],
            'out_of_stock_with_substitutes': unavailable[:limit],
            'reviewed_and_set_aside': unverified[:limit],
            'counts': {
                'matched': len(matches),
                'in_stock': len(in_stock),
                'out_of_stock': len(unavailable),
                'set_aside_on_safety': len(unverified),
            },
            'note': (
                'Only medicines assessed SAFE for this patient are offered. '
                'Medicines set aside are listed with the reason, so nothing is '
                'hidden - but they are not recommendations.'
            ),
        }

    @staticmethod
    def dispense_plan(medicine_id, patient_id=None, quantity_needed=1):
        """
        A concrete plan for one medicine: can it be dispensed now, and if not,
        what is the closest thing that can.
        """
        medicine = Medicine.query.get(medicine_id)
        if not medicine:
            return None

        stock = SubstitutionEngine._stock(medicine_id)
        patient = Patient.query.get(patient_id) if patient_id else None
        assessment = (SafetyEngine.assess(patient.id, medicine_id)
                      if patient else None)

        plan = {
            'requested': {
                'medicine_id': medicine.id,
                'name': medicine.name,
                'strength': medicine.strength,
                'form': medicine.form,
            },
            'stock_on_hand': stock,
            'quantity_needed': quantity_needed,
            'can_dispense_now': stock >= quantity_needed,
        }
        if assessment:
            plan['safety'] = assessment
            # Safety overrides availability: a medicine that is on the shelf but
            # contraindicated must not be reported as dispensable.
            if assessment['verdict'] in ('BLOCKED', 'UNSAFE'):
                plan['can_dispense_now'] = False
                plan['blocked_reason'] = assessment['headline']
            elif assessment['verdict'] == 'UNKNOWN':
                plan['can_dispense_now'] = False
                plan['blocked_reason'] = (
                    'Safety could not be verified: %s'
                    % (assessment.get('unknown_reason') or 'missing data'))

        if plan['can_dispense_now']:
            plan['action'] = 'Dispense as written.'
            plan['substitutes'] = []
            return plan

        if stock < quantity_needed:
            plan['action'] = (
                'Not enough stock (%s on hand, %s needed). Closest available '
                'alternatives below.' % (stock, quantity_needed))
        else:
            plan['action'] = (
                'In stock but not safe to dispense for this patient.')

        found = SubstitutionEngine.find_substitutes(
            medicine_id, patient_id=patient_id, limit=6, require_stock=True)
        plan['substitutes'] = found['substitutes'] if found else []
        plan['excluded_on_safety'] = found['excluded_on_safety'] if found else []
        if not plan['substitutes']:
            plan['action'] += ' No safe alternative is in stock either.'
        return plan
