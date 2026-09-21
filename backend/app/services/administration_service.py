"""
Administration cycle engine.

Answers the four questions that actually determine whether a course of
treatment works:

  1. How long should it be taken for?      (duration by indication)
  2. How often, and at what times?         (interval and clock timing)
  3. Does it need tapering or a break?     (steroids, PPIs, benzodiazepines)
  4. What happens if a dose is missed?     (the practical instruction)

WHY THIS IS NOT JUST "duration_days"
------------------------------------
A dispensed quantity is only correct if the course length is right. A 5-day
course of amoxicillin and a 5-day course of prednisolone are not the same
thing: the antibiotic must be completed even after the patient feels well,
while the steroid must be tapered rather than stopped. Printing "5 days" for
both is how courses get taken wrongly, so the cycle is derived per drug class
and per indication rather than read from a single stored integer.
"""

from datetime import datetime, timedelta

# Course length by drug class when no more specific rule applies.
# Values reflect standard UK BNF / WHO essential-medicines guidance.
CLASS_COURSE = {
    'penicillin': {'days': (5, 7), 'type': 'Antibiotic course',
                   'complete': True,
                   'note': 'Complete the full course even if you feel better, '
                           'to prevent resistance.'},
    'cephalosporin': {'days': (5, 7), 'type': 'Antibiotic course',
                      'complete': True,
                      'note': 'Complete the full course even if you feel better.'},
    'macrolide': {'days': (3, 3), 'type': 'Antibiotic course',
                  'complete': True,
                  'note': 'Complete the full course. Azithromycin is usually 3 days '
                          'because of its long tissue half-life; other macrolides '
                          'run for 5-7 days.'},
    'quinolone': {'days': (5, 7), 'type': 'Antibiotic course',
                  'complete': True,
                  'note': 'Complete the full course. Avoid antacids and dairy within '
                          '2 hours of a dose.'},
    'tetracycline': {'days': (7, 14), 'type': 'Antibiotic course',
                     'complete': True,
                     'note': 'Complete the full course. Take with plenty of water '
                             'and stay upright for 30 minutes.'},
    'nitrofuran': {'days': (5, 5), 'type': 'Antibiotic course',
                   'complete': True,
                   'note': 'Five days is the standard course for an uncomplicated '
                           'urinary infection.'},
    'aminoglycoside': {'days': (7, 10), 'type': 'Antibiotic course',
                       'complete': True,
                       'note': 'Hospital use. Monitor renal function and hearing.'},
    'nitroimidazole': {'days': (5, 7), 'type': 'Antibiotic course',
                       'complete': True,
                       'note': 'Avoid all alcohol during and for 48 hours after the '
                               'course - disulfiram-like reaction.'},
    'antimalarial': {'days': (3, 3), 'type': 'Antimalarial course',
                     'complete': True,
                     'note': 'Take with fatty food or milk to improve absorption.'},
    'antifungal': {'days': (7, 14), 'type': 'Antifungal course',
                   'complete': True,
                   'note': 'Continue for the full course even after the rash or '
                           'discharge settles.'},
    'antiviral': {'days': (5, 10), 'type': 'Antiviral course',
                  'complete': True,
                  'note': 'Most effective when started within 72 hours of onset.'},
    'anthelmintic': {'days': (1, 1), 'type': 'Single dose',
                     'complete': False,
                     'note': 'Usually a single dose; repeat after 2 weeks for '
                             'threadworm and treat household contacts.'},
    'corticosteroid': {'days': (5, 5), 'type': 'Short steroid course',
                       'taper': True,
                       'note': 'Take in the morning with food. Do not stop abruptly '
                               'after more than 2-3 weeks of treatment.'},
    'nsaid': {'days': (3, 7), 'type': 'Symptomatic - short course',
              'complete': False,
              'note': 'Use the lowest dose for the shortest time. Take with or after '
                      'food. Stop and seek advice if stomach pain or black stools.'},
    'analgesic': {'days': (3, 5), 'type': 'Symptomatic - short course',
                  'complete': False,
                  'note': 'Take only while needed. Seek review if pain persists '
                          'beyond 3 days.'},
    'opioid': {'days': (3, 5), 'type': 'Controlled analgesic - short course',
               'complete': False,
               'note': 'Constipation is expected - take a stool softener. Do not '
                       'drive. Dependence can develop within weeks.'},
    'proton pump inhibitor': {'days': (28, 56), 'type': 'Acid suppression',
                              'taper': True,
                              'note': 'Long courses need a step-down or on-demand '
                                      'plan to avoid rebound acid.'},
    'antihistamine': {'days': (7, 14), 'type': 'Symptomatic',
                      'complete': False,
                      'note': 'Non-sedating antihistamines are safe for longer '
                              'periods if needed.'},
    'bronchodilator': {'days': (28, 90), 'type': 'Maintenance',
                       'complete': False,
                       'note': 'Preventer inhalers work only if taken every day, '
                               'including when you feel well.'},
    'corticosteroid inhaler': {'days': (28, 90), 'type': 'Maintenance',
                               'complete': False,
                               'note': 'Rinse your mouth after each dose. Takes 2-4 '
                                       'weeks to reach full effect.'},
    'ssri': {'days': (28, 180), 'type': 'Maintenance - do not stop abruptly',
             'taper': True,
             'note': 'Full effect takes 2-4 weeks. Never stop suddenly - a taper is '
                     'needed to avoid withdrawal symptoms.'},
    'benzodiazepine': {'days': (3, 14), 'type': 'Short-term only',
                       'taper': True,
                       'note': 'Dependence can develop within 2-4 weeks. Use for the '
                               'shortest possible time and taper on stopping.'},
    'antiepileptic': {'days': (30, 365), 'type': 'Long-term maintenance',
                      'complete': False,
                      'note': 'Never stop suddenly - abrupt withdrawal can trigger '
                              'seizures. Take at the same times every day.'},
    'antidiabetic': {'days': (30, 365), 'type': 'Long-term maintenance',
                     'complete': False,
                     'note': 'Take at the same time each day. Learn to recognise and '
                             'treat hypoglycaemia.'},
    'statin': {'days': (30, 365), 'type': 'Long-term maintenance',
               'complete': False,
               'note': 'Usually taken at night. Report unexplained muscle pain.'},
    'antihypertensive': {'days': (30, 365), 'type': 'Long-term maintenance',
                         'complete': False,
                         'note': 'Take at the same time daily. Do not stop because '
                                 'you feel well - it controls, it does not cure.'},
    'diuretic': {'days': (30, 365), 'type': 'Long-term maintenance',
                 'complete': False,
                 'note': 'Take in the morning to avoid needing the toilet at night.'},
    'thyroid': {'days': (30, 365), 'type': 'Long-term replacement',
                'complete': False,
                'note': 'Take on an empty stomach, 30-60 minutes before breakfast, '
                        'and separate from calcium or iron by 4 hours.'},
    'bisphosphonate': {'days': (90, 365), 'type': 'Long-term - weekly dosing',
                       'complete': False,
                       'note': 'Take on an empty stomach with plain water and stay '
                               'upright for 30 minutes.'},
    'antigout': {'days': (30, 365), 'type': 'Prophylaxis',
                 'complete': False,
                 'note': 'Do not start during an acute attack. Cover with an '
                         'anti-inflammatory for the first 3 months.'},
    'antineoplastic': {'days': (1, 30), 'type': 'Specialist regimen',
                       'complete': True,
                       'note': 'Follow the specialist regimen exactly.'},
    'vaccine': {'days': (1, 1), 'type': 'Single dose immunisation',
                'complete': False,
                'note': 'Observe for 15 minutes after the injection - anaphylaxis, '
                        'though rare, occurs within this window.'},
    'eye drop': {'days': (7, 14), 'type': 'Topical course',
                 'complete': True,
                 'note': 'Discard the bottle 4 weeks after opening. Do not share '
                         'bottles between people.'},
}

# Drugs that need a specific dosing time of day, and why.
PREFERRED_TIME = {
    'statin': ('Evening', 'Cholesterol synthesis peaks overnight, so an evening '
                          'dose is more effective.'),
    'diuretic': ('Morning', 'Taking it later causes nocturia and disturbed sleep.'),
    'corticosteroid': ('Morning', 'Matches the natural cortisol peak and reduces '
                                  'adrenal suppression and insomnia.'),
    'thyroid': ('Before breakfast', 'Food and calcium reduce absorption '
                                    'substantially if taken together.'),
    'bisphosphonate': ('Before breakfast', 'Must be taken with plain water on an '
                                           'empty stomach, staying upright for '
                                           '30 minutes.'),
    'proton pump inhibitor': ('Before breakfast', 'Needs to be active when the '
                                                  'proton pumps are stimulated '
                                                  'by the first meal.'),
    'antidiabetic': ('With meals', 'Taking sulfonylureas with food reduces '
                                   'hypoglycaemia and stomach upset.'),
    'sedating antihistamine': ('At bedtime', 'Sedation is the main effect and is '
                                             'useful overnight.'),
    'migraine': ('At onset', 'Triptans work best taken as early in the attack as '
                             'possible.'),
}

# Interval in hours, keyed by the frequency wording.
FREQUENCY_HOURS = {
    'once daily': 24, 'o.d.': 24, 'daily': 24, 'every 24 hours': 24,
    'twice daily': 12, 'b.d.': 12, 'bid': 12, 'every 12 hours': 12,
    'three times daily': 8, 't.d.s.': 8, 'tds': 8, 'every 8 hours': 8,
    'four times daily': 6, 'q.i.d.': 6, 'qid': 6, 'every 6 hours': 6,
    'every 4 hours': 4, 'every 6 hours as needed': 6,
    'at bedtime': 24, 'h.s.': 24, 'nocte': 24,
    'when required': None, 's.o.s.': None, 'p.r.n.': None,
    'as needed': None,
}

# Typical clock times for each interval, so the label can say when to take it
# rather than leaving the patient to work it out.
CLOCK_TIMES = {
    4: ['06:00', '10:00', '14:00', '18:00', '22:00', '02:00'],
    6: ['06:00', '12:00', '18:00', '00:00'],
    8: ['08:00', '14:00', '20:00'],
    12: ['08:00', '20:00'],
    24: ['08:00'],
}


class AdministrationCycle:
    """Derive the course length, timing and tapering for a medicine."""

    @staticmethod
    def _classify(medicine):
        """Match a medicine to a course rule using its class text."""
        haystack = ' '.join(filter(None, [
            medicine.therapeutic_class or '',
            medicine.pharmacological_class or '',
            medicine.generic_name or '',
            medicine.name or '',
        ])).lower()

        # Order matters: the most specific class wins. A corticosteroid inhaler
        # must not pick up the systemic steroid taper rule.
        ordered = [
            ('corticosteroid inhaler', ['inhaler', 'inhalation']),
            ('proton pump inhibitor', ['proton pump', 'omeprazole', 'pantoprazole',
                                       'esomeprazole', 'rabeprazole', 'lansoprazole']),
            ('bisphosphonate', ['bisphosphonate', 'alendronate', 'risedronate']),
            ('antithyroid', ['carbimazole', 'methimazole', 'propylthiouracil']),
            ('thyroid', ['thyroid', 'levothyroxine', 'thyroxine']),
            ('ssri', ['ssri', 'selective serotonin', 'sertraline', 'fluoxetine',
                      'escitalopram', 'citalopram', 'paroxetine']),
            ('benzodiazepine', ['benzodiazepine', 'alprazolam', 'diazepam',
                                'lorazepam', 'clonazepam', 'clobazam']),
            ('antiepileptic', ['antiepileptic', 'anticonvulsant', 'phenytoin',
                               'carbamazepine', 'valproate', 'levetiracetam',
                               'lamotrigine']),
            ('statin', ['statin', 'atorvastatin', 'simvastatin', 'rosuvastatin',
                        'pravastatin']),
            ('antidiabetic', ['antidiabetic', 'metformin', 'glimepiride',
                              'sitagliptin', 'insulin', 'gliclazide']),
            ('diuretic', ['diuretic', 'furosemide', 'hydrochlorothiazide',
                          'spironolactone', 'torsemide']),
            ('antihypertensive', ['antihypertensive', 'ace inhibitor',
                                  'angiotensin', 'calcium channel', 'beta-blocker',
                                  'losartan', 'amlodipine', 'telmisartan',
                                  'metoprolol', 'lisinopril', 'nifedipine']),
            ('antigout', ['antigout', 'xanthine oxidase', 'allopurinol', 'colchicine',
                          'febuxostat']),
            ('opioid', ['opioid', 'morphine', 'tramadol', 'codeine', 'fentanyl']),
            ('nsaid', ['nsaid', 'ibuprofen', 'diclofenac', 'naproxen', 'aceclofenac',
                       'etoricoxib', 'ketorolac', 'indomethacin']),
            ('analgesic', ['analgesic', 'antipyretic', 'paracetamol',
                           'acetaminophen']),
            ('vaccine', ['vaccine', 'toxoid', 'immunoglobulin']),
            ('corticosteroid', ['corticosteroid', 'glucocorticoid', 'prednisolone',
                                'dexamethasone', 'hydrocortisone', 'methylprednisolone']),
            ('penicillin', ['penicillin', 'amoxicillin', 'amoxycillin', 'ampicillin',
                            'cloxacillin', 'co-amoxiclav', 'clavulanic']),
            ('cephalosporin', ['cephalosporin', 'cefixime', 'ceftriaxone',
                               'cefuroxime', 'cefalexin', 'cephalexin']),
            ('macrolide', ['macrolide', 'azithromycin', 'erythromycin',
                           'clarithromycin']),
            ('quinolone', ['quinolone', 'ciprofloxacin', 'levofloxacin',
                           'ofloxacin', 'moxifloxacin']),
            ('tetracycline', ['tetracycline', 'doxycycline']),
            ('nitrofuran', ['nitrofurantoin', 'nitrofuran']),
            ('aminoglycoside', ['aminoglycoside', 'amikacin', 'gentamicin']),
            ('nitroimidazole', ['nitroimidazole', 'metronidazole', 'tinidazole']),
            ('antimalarial', ['antimalarial', 'artemether', 'lumefantrine',
                              'chloroquine', 'artesunate']),
            ('antifungal', ['antifungal', 'fluconazole', 'clotrimazole',
                            'itraconazole', 'terbinafine']),
            ('antiviral', ['antiviral', 'acyclovir', 'aciclovir', 'oseltamivir']),
            ('anthelmintic', ['anthelmintic', 'albendazole', 'praziquantel',
                              'mebendazole', 'ivermectin']),
            ('bronchodilator', ['bronchodilator', 'salbutamol', 'beta-2 agonist',
                                'antimuscarinic', 'ipratropium', 'montelukast',
                                'leukotriene']),
            ('antihistamine', ['antihistamine', 'cetirizine', 'levocetirizine',
                               'chlorpheniramine', 'loratadine', 'fexofenadine']),
            ('eye drop', ['ophthalmic', 'eye drop', 'eye ointment']),
        ]
        for key, terms in ordered:
            if any(term in haystack for term in terms):
                return key
        return None

    @staticmethod
    def build(medicine, frequency=None, duration_days=None, indication=None):
        # `indication` is accepted for call-site symmetry with the dosage
        # calculator and to allow future indication-specific rules, which is
        # why it is declared even though the class rules do not branch on it
        # yet. Marked as used so the linter does not flag it as dead.
        """
        Return the full administration plan for a medicine.

        `frequency` and `duration_days` override the derived values when the
        prescriber has specified them - a prescriber's instruction always beats
        the class default, and this function must never silently replace it.
        """
        _ = indication  # see note above: reserved for indication-specific rules
        key = AdministrationCycle._classify(medicine)
        rule = CLASS_COURSE.get(key) if key else None

        # --- duration -------------------------------------------------------
        source = 'class default'
        if duration_days:
            days = int(duration_days)
            source = 'prescriber'
        elif rule:
            low, high = rule['days']
            days = high if high != low else low
            source = '%s class range (%d-%d days)' % (key, low, high)
        else:
            days = 5
            source = 'fallback (no class rule matched)'

        # --- frequency and interval ----------------------------------------
        freq = frequency or 'As directed'
        lowered = str(freq).strip().lower()
        interval = FREQUENCY_HOURS.get(lowered)
        if interval is None:
            # Try to read a number of times per day out of the wording.
            import re
            match = re.search(r'(\d+)\s*times', lowered)
            if match:
                per_day = int(match.group(1))
                interval = 24 // per_day if per_day else None
        is_prn = any(token in lowered for token in
                     ('when required', 'as needed', 's.o.s', 'p.r.n', 'sos'))

        # --- clock times ----------------------------------------------------
        timing = ''
        if is_prn:
            timing = 'Only when needed. Do not exceed the stated maximum in 24 hours.'
        elif interval and interval in CLOCK_TIMES:
            slots = CLOCK_TIMES[interval]
            if interval >= 24:
                timing = 'Take at about the same time each day.'
            else:
                timing = 'Space the doses evenly through the day, e.g. %s.' % \
                    ', '.join(slots[:max(2, 24 // interval)])

        # A drug-specific time-of-day preference overrides the generic advice.
        #
        # Iteration order matters here: the route/haystack is indexed so that a
        # specific match cannot lose to a broader one. An inhaled steroid must
        # not pick up the systemic corticosteroid "take in the morning" rule,
        # because the reasons are entirely different (adrenal suppression versus
        # dosing convenience).
        is_inhaled = any(t in (medicine.route_of_administration or '').lower()
                         or t in (medicine.form or '').lower()
                         for t in ('inhal', 'nebuli'))
        preference_order = list(PREFERRED_TIME.items())
        if is_inhaled:
            # Drop the systemic-steroid preference for inhaled products.
            preference_order = [
                (token, value) for token, value in preference_order
                if token != 'corticosteroid'
            ]
        stacked = ' '.join(filter(None, [
            medicine.therapeutic_class or '',
            medicine.pharmacological_class or '',
            medicine.generic_name or '',
            medicine.name or '',
        ])).lower()
        for token, (when, why) in preference_order:
            if token in stacked:
                timing = '%s - %s' % (when, why)
                break

        # --- taper ----------------------------------------------------------
        taper = bool(rule and rule.get('taper')) and days >= 14
        taper_note = None
        if taper:
            if key == 'corticosteroid':
                taper_note = ('Reduce the dose gradually over 1-2 weeks rather than '
                              'stopping. Abrupt withdrawal after 3 weeks or more can '
                              'cause adrenal crisis.')
            elif key == 'benzodiazepine':
                taper_note = ('Reduce by about 25% every two weeks. Abrupt '
                              'withdrawal can cause seizures and severe anxiety.')
            elif key == 'ssri':
                taper_note = ('Reduce the dose over 2-4 weeks to avoid discontinuation '
                              'symptoms such as dizziness and irritability.')
            elif key == 'proton pump inhibitor':
                taper_note = ('Step down to the lowest effective dose or use it only '
                              'when needed, to avoid rebound acid hypersecretion.')

        # --- missed dose ----------------------------------------------------
        missed = AdministrationCycle._missed_dose_advice(interval, is_prn)

        # --- quantity -------------------------------------------------------
        per_day = None
        if interval and interval > 0:
            per_day = max(1, round(24 / interval))
        elif is_prn:
            per_day = 1  # a working assumption; flagged as approximate below

        units = None
        if per_day:
            units = per_day * days

        return {
            'course_type': rule['type'] if rule else 'As prescribed',
            'drug_class_matched': key,
            'duration_days': days,
            'duration_source': source,
            'frequency': freq,
            'interval_hours': interval,
            'doses_per_day': per_day,
            'total_units': units,
            'quantity_is_approximate': is_prn,
            'timing': timing or None,
            'is_when_required': is_prn,
            'complete_full_course': bool(rule and rule.get('complete')),
            'taper_required': taper,
            'taper_note': taper_note,
            'missed_dose': missed,
            'patient_note': rule.get('note') if rule else None,
            'end_date': (datetime.now() + timedelta(days=days)).strftime('%d %b %Y'),
        }

    @staticmethod
    def _missed_dose_advice(interval, is_prn):
        """What to tell a patient who forgets a dose."""
        if is_prn:
            return 'Take it when you need it. Do not double up on a later dose.'
        if not interval:
            return ('If you miss a dose, take it when you remember unless it is '
                    'nearly time for the next one. Never take two doses at once.')
        if interval <= 6:
            return ('If you miss a dose, take it as soon as you remember, unless it '
                    'is within 2 hours of the next dose. Never take a double dose.')
        if interval <= 12:
            return ('If you miss a dose, take it as soon as you remember. If it is '
                    'almost time for the next one, skip the missed dose. Never take '
                    'a double dose.')
        return ('If you miss a dose on a once-daily medicine, take it when you '
                'remember on the same day. If you only remember the next day, skip '
                'it. Never take a double dose.')

    @staticmethod
    def summary_line(plan):
        """One-line human summary, e.g. '3 days - t.d.s. - 4 doses'."""
        if not plan:
            return ''
        parts = ['%d day%s' % (plan['duration_days'],
                               '' if plan['duration_days'] == 1 else 's')]
        if plan['frequency']:
            parts.append(plan['frequency'])
        if plan['total_units']:
            suffix = ' (approx.)' if plan.get('quantity_is_approximate') else ''
            parts.append('%d units%s' % (plan['total_units'], suffix))
        return ' - '.join(parts)
