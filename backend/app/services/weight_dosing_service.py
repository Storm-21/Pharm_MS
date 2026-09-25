"""
Weight-based dosing formulas.

WHY THIS MODULE EXISTS
----------------------
Paediatric and many adult doses are prescribed per kilogram of body weight, and
that calculation is the single most error-prone piece of arithmetic in a
pharmacy. It is deliberately isolated here so that the formula, the cap and the
explanatory text are written once, unit-tested once, and can be read by a
clinician without hunting through route code.

FORMULAS IMPLEMENTED
--------------------
1. **mg/kg (weight-based)** - the primary method. ``dose = mg_per_kg * weight``.
   This is how paediatric doses are actually published and is always preferred
   when a per-kilogram figure exists and a weight is on file.

2. **BSA (Mosteller)** - ``BSA = sqrt(height_cm * weight_kg / 3600)``.
   Used where a medicine is dosed per square metre (cytotoxics, some
   biologicals, paediatric infusions) or as the cross-check on an mg/kg figure
   for an unusually heavy or light patient.

3. **Clark's rule** - ``child dose = adult dose * weight_lb / 150``.
   A weight-based fallback for medicines that have no published mg/kg figure.
   It is weaker than mg/kg but is weight-based, which the age formulas are not,
   so it is preferred over them whenever a weight is recorded.

4. **Young's rule** - ``child dose = adult dose * age / (age + 12)``.
   Last resort, because it ignores weight entirely under the assumption of an
   average-sized child. Used only when no weight is on file.

EVERY RESULT CARRIES
--------------------
    method          which formula produced the number
    formula         the literal expression, so it can be shown and checked
    inputs          the numbers that went in
    steps           the arithmetic, line by line
    capped          whether a maximum was applied, and which
    confidence      documented | moderate | low
    warnings        anything the prescriber must read

Nothing is rounded away before the cap is applied, no dose is ever emitted
above the medicine's single-dose maximum, and no weight is ever invented: a
missing weight produces an explicit "weight not recorded" result rather than a
silently assumed 70 kg adult, which is the mistake that causes real harm.
"""

import math

# 1 kg = 2.20462 lb, for Clark's rule which is defined in pounds.
KG_TO_LB = 2.2046226218487757

# The reference weight Clark's rule is normalised to: an adult dose is what a
# 150 lb (68 kg) adult receives.
CLARK_ADULT_WEIGHT_LB = 150.0


class DosingFormula:
    """The published formulas, each a pure function with no database access."""

    @staticmethod
    def weight_based(mg_per_kg, weight_kg):
        """dose = mg_per_kg x weight_kg. The primary paediatric method."""
        return float(mg_per_kg) * float(weight_kg)

    @staticmethod
    def bsa_mosteller(height_cm, weight_kg):
        """BSA in m^2. Mosteller: sqrt(height_cm x weight_kg / 3600)."""
        return math.sqrt(float(height_cm) * float(weight_kg) / 3600.0)

    @staticmethod
    def bsa_based(dose_per_m2, bsa_m2):
        """dose = dose_per_m2 x BSA."""
        return float(dose_per_m2) * float(bsa_m2)

    @staticmethod
    def clarks_rule(adult_dose_mg, weight_kg):
        """Clark's rule: adult dose x (weight in lb / 150)."""
        weight_lb = float(weight_kg) * KG_TO_LB
        return float(adult_dose_mg) * (weight_lb / CLARK_ADULT_WEIGHT_LB)

    @staticmethod
    def youngs_rule(adult_dose_mg, age_years):
        """Young's rule: adult dose x age / (age + 12). Age only, no weight."""
        age = float(age_years)
        return float(adult_dose_mg) * (age / (age + 12.0))


def _round_dose(value):
    """Round to 3 dp below 1 mg (levothyroxine, digoxin) and 2 dp otherwise.

    Sub-milligram drugs are dosed in fractions of a microgram, so a blanket
    2 dp round would collapse 0.0625 mg to 0.06 - a real ~4% error for a drug
    with a narrow therapeutic index.
    """
    if value is None:
        return None
    if abs(value) < 1:
        return round(value, 3)
    return round(value, 2)


class WeightDoser:
    """Turn a patient and a medicine's reference dose into a checked dose."""

    @staticmethod
    def calculate(
        patient,
        reference,
        *,
        medicine=None,
        prefer_bsa=False,
        bsa_dose_per_m2=None,
        doses_per_day=1,
        max_daily_dose_mg=None,
        method=None,
    ):
        """
        Build a dose for ``patient`` from a ``reference`` dose record.

        ``reference`` keys (all optional except as noted):
            adult_mg    standard adult single dose, used by Clark/Young
            mg_per_kg   paediatric single dose per kg - the preferred figure
            max_mg      single-dose ceiling applied after the calculation
            max_daily_mg daily ceiling, an alternative to max_daily_dose_mg

        ``prefer_bsa`` selects the BSA route when ``bsa_dose_per_m2`` is given.
        It is only ever used when explicitly requested, because most medicines
        in this database are dosed per kg, not per m^2.

        ``method`` lets the prescriber pick the formula themselves instead of
        taking the evidence-ranked default: 'mg/kg', 'bsa', 'clark' or 'young'.
        An explicit choice is honoured only when its inputs exist - asking for
        BSA with no height, or Clark with no weight, falls back to the default
        route and says so in ``warnings`` rather than inventing an input.

        Returns a dict describing the dose and, crucially, how it was reached.
        Returns ``None`` only when there is nothing whatsoever to calculate
        from, so the caller can say "cannot calculate" rather than show a zero.
        """
        reference = reference or {}
        adult_mg = reference.get('adult_mg')
        mg_per_kg = reference.get('mg_per_kg')
        max_mg = reference.get('max_mg') or adult_mg
        daily_ceiling = reference.get('max_daily_mg') or max_daily_dose_mg

        age = float(patient.age or 0)
        age_months = float(getattr(patient, 'age_months', 0) or 0)
        weight_kg = getattr(patient, 'weight_kg', None)
        height_known = bool(getattr(patient, 'height_cm', None))

        warnings = []
        steps = []

        # --- Route selection -------------------------------------------------
        # Ordered by evidential strength: an explicit mg/kg figure beats a
        # derived BSA dose, which beats a weight-normalised adult dose, which
        # beats an age-only estimate.
        #
        # ``requested_method`` holds the caller's choice; the descriptive
        # ``method`` is set below once a route has been chosen. They must stay
        # separate: this line previously read ``method = None``, which silently
        # discarded the prescriber's selection before it was ever read.
        requested_method = method
        method = None
        formula = None
        inputs = {}
        dose = None
        confidence = 'low'
        route = None

        bsa_available = bool(weight_kg and patient.bsa_m2)

        # --- Age-based comparison -------------------------------------------
        # Computed on every call, not only when it is the chosen route. Both
        # formulas are shown side by side on the dosage panel so the prescriber
        # can see how far apart they are and judge which suits the patient.
        # Showing only the winner would hide exactly the disagreement that is
        # worth knowing about - a 24 kg eight-year-old is dosed 412.5 mg by
        # weight and 250 mg by the age band, and that gap is the point.
        age_comparison = None
        if adult_mg and mg_per_kg and weight_kg:
            # Only useful when the weight-based route is genuinely available and
            # therefore differs. With no weight on file the chosen dose IS
            # Young's rule, so showing the pair would print the same number
            # twice and imply a comparison that does not exist.
            age_dose = DosingFormula.youngs_rule(adult_mg, age)
            age_comparison = {
                'method': "Young's rule (age-based)",
                'formula': 'adult dose %s mg x %s / (%s + 12)' % (adult_mg, age, age),
                'dose': _round_dose(age_dose),
                'unit': 'mg',
                'inputs': {'adult_mg': adult_mg, 'age_years': age},
                'is_weight_based': False,
                'assumes': 'an average-sized child of this age - it does not use weight',
            }
            if max_mg and age_comparison['dose'] > max_mg:
                age_comparison['dose'] = _round_dose(float(max_mg))
                age_comparison['capped'] = True

        if prefer_bsa and bsa_dose_per_m2 and bsa_available:
            route = 'bsa'
        elif mg_per_kg and weight_kg:
            route = 'weight'
        elif weight_kg and adult_mg:
            route = 'clark'
        elif prefer_bsa and bsa_dose_per_m2 and not bsa_available:
            # Asked for BSA but no weight to build it from - fall through to an
            # age estimate and say exactly why.
            warnings.append(
                'BSA dosing requested but BSA cannot be computed without a '
                'weight, so an age-based estimate was used instead.')
            route = 'young'
        else:
            route = 'young'

        # --- An explicit choice by the prescriber ----------------------------
        # The route chosen above is the evidence-ranked default. When a method
        # was named, honour it if its inputs exist; otherwise keep the default
        # and explain, because silently calculating something other than what
        # was asked for is worse than refusing.
        if requested_method:
            requested = str(requested_method).strip().lower()
            aliases = {
                'mg/kg': 'weight', 'mgkg': 'weight', 'mg per kg': 'weight',
                'weight': 'weight', 'weight-based': 'weight',
                'weight_based': 'weight',
                'bsa': 'bsa', 'body surface area': 'bsa', 'mosteller': 'bsa',
                "clark's rule": 'clark', 'clarks rule': 'clark',
                'clarks': 'clark', 'clark': 'clark',
                "young's rule": 'young', 'youngs rule': 'young',
                'youngs': 'young', 'young': 'young', 'age': 'young',
            }
            wanted = aliases.get(requested)
            if wanted is None:
                warnings.append('Unknown dose method "%s"; the default was used.'
                                % requested_method)
            elif wanted == route:
                pass  # the requested formula is already the one in use
            elif wanted == 'bsa' and bsa_dose_per_m2 and bsa_available:
                route = 'bsa'
            elif wanted == 'weight' and mg_per_kg and weight_kg:
                route = 'weight'
            elif wanted == 'clark' and weight_kg and adult_mg:
                route = 'clark'
            elif wanted == 'young' and adult_mg:
                route = 'young'
            else:
                warnings.append(
                    'The %s formula was requested but its inputs are not on '
                    'file, so the default route was used instead.'
                    % requested_method)

        if route == 'bsa':
            bsa = patient.bsa_m2
            dose = DosingFormula.bsa_based(bsa_dose_per_m2, bsa)
            method = 'Body surface area (Mosteller)'
            formula = '%s per m2 x %s m2' % (bsa_dose_per_m2, bsa)
            inputs = {
                'dose_per_m2': bsa_dose_per_m2,
                'bsa_m2': bsa,
                'weight_kg': weight_kg,
                'height_cm': getattr(patient, 'height_cm', None),
            }
            steps.append('BSA = sqrt(%s x %s / 3600) = %s m2'
                         % (getattr(patient, 'height_cm', None) or 165.0,
                            weight_kg, bsa))
            steps.append('Dose = %s mg/m2 x %s m2 = %s mg'
                         % (bsa_dose_per_m2, bsa, _round_dose(dose)))
            confidence = 'documented'
            # A per-m2 dose has no adult_mg-derived single-dose ceiling. Using
            # the ordinary adult dose as a cap here would silently truncate a
            # legitimate BSA dose (e.g. 100 mg/m2 x 1.84 m2 = 184 mg, which the
            # 100 mg adult reference would wrongly cut to 100 mg), so the cap is
            # only applied when a ceiling was supplied explicitly.
            max_mg = reference.get('max_mg')
            if not height_known:
                warnings.append(
                    'No height recorded, so BSA was computed from an assumed '
                    'average height. Record the height for an exact figure.')

        elif route == 'weight':
            dose = DosingFormula.weight_based(mg_per_kg, weight_kg)
            method = 'Weight-based (mg/kg)'
            formula = '%s mg/kg x %s kg' % (mg_per_kg, weight_kg)
            inputs = {'mg_per_kg': mg_per_kg, 'weight_kg': weight_kg}
            steps.append('Dose = %s mg/kg x %s kg = %s mg'
                         % (mg_per_kg, weight_kg, _round_dose(dose)))
            confidence = 'documented'

        elif route == 'clark':
            dose = DosingFormula.clarks_rule(adult_mg, weight_kg)
            weight_lb = weight_kg * KG_TO_LB
            method = "Clark's rule (weight-based)"
            formula = '%s mg x (%s lb / 150)' % (adult_mg, round(weight_lb, 1))
            inputs = {
                'adult_mg': adult_mg,
                'weight_kg': weight_kg,
                'weight_lb': round(weight_lb, 1),
            }
            steps.append('Weight = %s kg = %s lb' % (weight_kg, round(weight_lb, 1)))
            steps.append('Dose = %s mg x (%s / 150) = %s mg'
                         % (adult_mg, round(weight_lb, 1), _round_dose(dose)))
            warnings.append(
                'No published mg/kg dose for this medicine, so the adult dose '
                'was scaled by body weight (Clark\'s rule). Verify with a '
                'prescriber.')
            confidence = 'moderate'

        else:  # young
            dose = DosingFormula.youngs_rule(adult_mg, age)
            method = "Young's rule (age only)"
            formula = '%s mg x %s / (%s + 12)' % (adult_mg, age, age)
            inputs = {'adult_mg': adult_mg, 'age_years': age}
            steps.append('Dose = %s mg x %s / %s = %s mg'
                         % (adult_mg, age, age + 12, _round_dose(dose)))
            if weight_kg:
                # A weight exists but the drug has no mg/kg figure and no
                # adult_mg/BSA route applied - note it, because a weight-based
                # route would normally be preferred.
                warnings.append(
                    'An age formula was used even though a weight is recorded. '
                    'No weight-based dose is published for this medicine.')
            else:
                warnings.append(
                    'No weight recorded, so the dose is an age-based estimate. '
                    'Record the weight for a weight-based dose.')
            confidence = 'moderate'

        if dose is None:
            return None

        # --- Ceilings --------------------------------------------------------
        # Order matters: the single-dose cap first, then the daily cap, so the
        # reported number is never above either. Both are re-checked by the
        # safety engine, but a calculator that emits an impossible dose and
        # relies on a later layer to catch it is not trustworthy on its own.
        capped = False
        caps_applied = []

        if max_mg and dose > max_mg:
            steps.append('Capped at the single-dose maximum: %s mg > %s mg'
                         % (_round_dose(dose), max_mg))
            dose = float(max_mg)
            capped = True
            caps_applied.append('single dose %s mg' % max_mg)

        if daily_ceiling and doses_per_day:
            daily = dose * float(doses_per_day)
            if daily > daily_ceiling:
                allowed_single = float(daily_ceiling) / float(doses_per_day)
                steps.append(
                    'Daily total %s mg exceeds the %s mg/day ceiling, so the '
                    'single dose is reduced to %s mg'
                    % (_round_dose(daily), daily_ceiling, _round_dose(allowed_single)))
                dose = allowed_single
                capped = True
                caps_applied.append('daily total %s mg/day' % daily_ceiling)

        dose = _round_dose(dose)

        if capped:
            warnings.append('Dose capped to stay within the %s limit(s).'
                            % ' and '.join(caps_applied))

        # --- Sanity ----------------------------------------------------------
        if dose <= 0:
            return None

        return {
            'method': method,
            'formula': formula,
            'route': route,
            'inputs': inputs,
            'steps': steps,
            'dose': dose,
            'unit': 'mg',
            'confidence': confidence,
            'capped': capped,
            'caps_applied': caps_applied,
            'max_single_dose_mg': max_mg,
            'max_daily_dose_mg': daily_ceiling,
            'daily_total_mg': _round_dose(dose * float(doses_per_day or 1)),
            'doses_per_day': doses_per_day,
            'weight_kg': weight_kg,
            'age_years': age,
            'age_months': age_months,
            'bsa_m2': patient.bsa_m2,
            'bmi': getattr(patient, 'bmi', None),
            'warnings': warnings,
            'is_weight_based': route in ('weight', 'clark', 'bsa'),
            # Both methods, so the panel can show them together.
            'formulas': [
                {
                    'method': method,
                    'formula': formula,
                    'dose': dose,
                    'unit': 'mg',
                    'is_weight_based': route in ('weight', 'clark', 'bsa'),
                    'selected': True,
                },
                dict(age_comparison, selected=False) if age_comparison else None,
            ] if age_comparison else [
                {
                    'method': method,
                    'formula': formula,
                    'dose': dose,
                    'unit': 'mg',
                    'is_weight_based': route in ('weight', 'clark', 'bsa'),
                    'selected': True,
                },
            ],
        }

    @staticmethod
    def describe(result):
        """One-line human summary of a dose result, for notes and reports."""
        if not result:
            return 'Dose could not be calculated.'
        line = '%s mg - %s (%s)' % (
            result['dose'], result['method'], result['formula'])
        if result.get('caps_applied'):
            line += '; capped: %s' % ', '.join(result['caps_applied'])
        return line

    # ------------------------------------------------------------------
    # Every formula at once, so the prescriber can choose rather than
    # accept the automatic route.
    # ------------------------------------------------------------------
    # The order below is the order the panel shows them and the order of
    # preference: a published mg/kg figure first, then BSA, then a
    # weight-scaled adult dose, then an age estimate. ``usable`` is false when
    # a formula's inputs are missing - a blank weight disables Clark just as a
    # blank height disables BSA - and the reason is always stated, because a
    # greyed-out option with no explanation is worse than no option at all.
    FORMULA_SPECS = (
        ('mg/kg', 'Weight-based (mg/kg)',
         'dose = mg_per_kg x weight_kg',
         'The published paediatric method. Preferred whenever a per-kilogram '
         'figure exists and the weight is recorded.',
         'documented'),
        ('bsa', 'Body surface area (Mosteller)',
         'BSA = sqrt(height_cm x weight_kg / 3600); dose = dose_per_m2 x BSA',
         'Used for medicines dosed per square metre - cytotoxics, some '
         'biologicals and paediatric infusions.',
         'documented'),
        ('clark', "Clark's rule (weight-scaled adult dose)",
         'dose = adult_dose x (weight_lb / 150)',
         'A weight-based fallback for medicines with no published mg/kg '
         'figure. Weaker than mg/kg but still uses the patient\u2019s weight.',
         'moderate'),
        ('young', "Young's rule (age only)",
         'dose = adult_dose x age / (age + 12)',
         'Last resort. It ignores weight and assumes an average-sized child '
         'of that age.',
         'low'),
    )

    @staticmethod
    def all_formulas(
        patient,
        reference,
        *,
        bsa_dose_per_m2=None,
        doses_per_day=1,
        max_daily_dose_mg=None,
    ):
        """Every published formula, computed and annotated in one pass.

        Returns a list of dicts, each carrying its method, the literal formula,
        the resulting dose, whether it could actually be applied (``usable``)
        and - when it could not - the missing input in plain words. Nothing is
        dropped: a formula that cannot be applied is returned disabled with a
        reason, so the UI never has to guess why an option is unavailable.
        """
        reference = reference or {}
        adult_mg = reference.get('adult_mg')
        mg_per_kg = reference.get('mg_per_kg')
        max_mg = reference.get('max_mg') or adult_mg

        age = float(patient.age or 0)
        weight_kg = getattr(patient, 'weight_kg', None)
        height_cm = getattr(patient, 'height_cm', None)
        bsa_m2 = patient.bsa_m2
        weight_lb = (float(weight_kg) * KG_TO_LB) if weight_kg else None

        results = []
        for key, label, formula, note, confidence in WeightDoser.FORMULA_SPECS:
            usable = False
            reason = None
            dose = None
            inputs = {}
            steps = []

            if key == 'mg/kg':
                if not mg_per_kg:
                    reason = ('No published mg/kg figure is on file for this '
                              'medicine.')
                elif not weight_kg:
                    reason = 'The patient has no weight recorded.'
                else:
                    usable = True
                    dose = DosingFormula.weight_based(mg_per_kg, weight_kg)
                    inputs = {'mg_per_kg': mg_per_kg, 'weight_kg': weight_kg}
                    steps = [
                        'Dose = %s mg/kg x %s kg = %s mg'
                        % (mg_per_kg, weight_kg, _round_dose(dose)),
                    ]

            elif key == 'bsa':
                if not bsa_dose_per_m2:
                    reason = ('No per-m2 figure is on file for this medicine, '
                              'and none was entered.')
                elif not weight_kg:
                    reason = ('BSA cannot be computed without a weight on '
                              'file.')
                else:
                    usable = True
                    dose = DosingFormula.bsa_based(bsa_dose_per_m2, bsa_m2)
                    inputs = {
                        'dose_per_m2': bsa_dose_per_m2,
                        'bsa_m2': bsa_m2,
                        'weight_kg': weight_kg,
                        'height_cm': height_cm,
                    }
                    steps = [
                        'BSA = sqrt(%s x %s / 3600) = %s m2'
                        % (height_cm or '165 (assumed)', weight_kg, bsa_m2),
                        'Dose = %s per m2 x %s m2 = %s mg'
                        % (bsa_dose_per_m2, bsa_m2, _round_dose(dose)),
                    ]
                    if not height_cm:
                        note += (' No height recorded, so an average height was '
                                 'assumed for the BSA.')

            elif key == 'clark':
                if not adult_mg:
                    reason = 'No adult reference dose is on file for this medicine.'
                elif not weight_kg:
                    reason = 'The patient has no weight recorded.'
                else:
                    usable = True
                    dose = DosingFormula.clarks_rule(adult_mg, weight_kg)
                    inputs = {
                        'adult_mg': adult_mg,
                        'weight_kg': weight_kg,
                        'weight_lb': round(weight_lb, 1),
                    }
                    steps = [
                        'Weight = %s kg = %s lb'
                        % (weight_kg, round(weight_lb, 1)),
                        'Dose = %s mg x (%s / 150) = %s mg'
                        % (adult_mg, round(weight_lb, 1), _round_dose(dose)),
                    ]

            else:  # young
                if not adult_mg:
                    reason = 'No adult reference dose is on file for this medicine.'
                else:
                    usable = True
                    dose = DosingFormula.youngs_rule(adult_mg, age)
                    inputs = {'adult_mg': adult_mg, 'age_years': age}
                    steps = [
                        'Dose = %s mg x %s / (%s + 12) = %s mg'
                        % (adult_mg, age, age, _round_dose(dose)),
                    ]

            entry = {
                'key': key,
                'method': label,
                'formula': formula,
                'note': note,
                'confidence': confidence if usable else None,
                'usable': usable,
                'reason': reason,
                'inputs': inputs,
                'steps': steps,
                'dose': _round_dose(dose) if usable else None,
                'unit': 'mg',
                'is_weight_based': key in ('mg/kg', 'bsa', 'clark'),
                'capped': False,
            }

            # Apply the same ceilings here as the single-route calculator, for
            # each formula independently, so a comparison is never made between
            # a capped and an uncapped number.
            if usable:
                capped, caps = WeightDoser._apply_caps(
                    entry['dose'], max_mg, max_daily_dose_mg, doses_per_day)
                if capped:
                    entry['dose'] = _round_dose(
                        WeightDoser._capped_value(
                            float(entry['dose']), max_mg, max_daily_dose_mg,
                            doses_per_day))
                    entry['capped'] = True
                    entry['caps_applied'] = caps

            results.append(entry)

        return results

    @staticmethod
    def _apply_caps(dose, max_mg, daily_ceiling, doses_per_day):
        """Whether a single-dose or daily ceiling would trim this dose."""
        capped = False
        caps = []
        if max_mg and dose > max_mg:
            capped = True
            caps.append('single dose %s mg' % max_mg)
        if daily_ceiling and doses_per_day:
            if dose * float(doses_per_day) > float(daily_ceiling):
                capped = True
                caps.append('daily total %s mg/day' % daily_ceiling)
        return capped, caps

    @staticmethod
    def _capped_value(dose, max_mg, daily_ceiling, doses_per_day):
        """The dose after the single-dose then daily ceiling is applied."""
        if max_mg and dose > max_mg:
            dose = float(max_mg)
        if daily_ceiling and doses_per_day:
            daily = dose * float(doses_per_day)
            if daily > float(daily_ceiling):
                dose = float(daily_ceiling) / float(doses_per_day)
        return dose

    @staticmethod
    def combine(formulas, doses_per_day=1):
        """Report the agreement between every usable formula.

        This is the "combine them all" view. It does not average the numbers -
        averaging clinical doses has no basis and would invent a figure that no
        published method supports. What it does is state the spread: the lowest,
        the highest, how far apart they are as a percentage, and which methods
        agreed closely. Where the formulas disagree materially the caller is
        told to decide by judgement, because that disagreement is clinical
        information rather than an error to be averaged away.
        """
        usable = [f for f in (formulas or []) if f.get('usable') and f.get('dose')]
        if not usable:
            return {
                'usable_count': 0,
                'summary': ('No formula could be applied: the inputs they need '
                            'are not on file.'),
                'agreement': 'none',
                'doses': [],
            }

        doses = [float(f['dose']) for f in usable]
        low, high = min(doses), max(doses)
        reference = next(
            (f for f in usable if f.get('key') == 'mg/kg'),
            usable[0],
        )
        ref_dose = float(reference['dose'])

        # A single usable formula cannot "agree" with anything. Saying it agrees
        # within 5% reads as reassurance and is the opposite of the truth when
        # the one formula available is the weakest one: with no weight on file
        # the only usable method is Young's rule, and reporting agreement there
        # would tell a prescriber that an age estimate has been corroborated
        # when it is the sole figure that could be produced. "Nothing to compare"
        # and "they agree" are different facts and must read differently.
        if len(usable) == 1:
            only = usable[0]
            return {
                'usable_count': 1,
                'lowest': _round_dose(low),
                'highest': _round_dose(high),
                'spread_mg': 0,
                'spread_pct': 0.0,
                'reference_method': only['method'],
                'reference_dose': _round_dose(ref_dose),
                'agreement': 'single',
                'verdict': (
                    'Only one formula could be applied - %s - so there is '
                    'nothing to compare it against. %s'
                    % (only['method'], only.get('note') or '')
                ).strip(),
                'daily_totals': [
                    {
                        'method': only['method'],
                        'single': _round_dose(ref_dose),
                        'daily': _round_dose(ref_dose * float(doses_per_day or 1)),
                        'capped': only.get('capped', False),
                    }
                ],
                'doses': [_round_dose(d) for d in doses],
            }

        # Spread as a percentage of the preferred figure, so the prescriber can
        # judge materiality rather than reading an absolute milligram gap.
        spread_pct = ((high - low) / ref_dose * 100.0) if ref_dose else 0.0
        if spread_pct <= 5:
            agreement = 'close'
            verdict = ('All %d applicable formulas agree within 5%%. Any of them '
                       'is reasonable to dispense.' % len(usable))
        elif spread_pct <= 20:
            agreement = 'moderate'
            verdict = ('The formulas differ by up to %.0f%%. Prefer the '
                       'weight-based figure and confirm with the prescriber '
                       'if the patient is at either extreme of size.' % spread_pct)
        else:
            agreement = 'wide'
            verdict = ('The formulas differ by up to %.0f%%, which is material. '
                       'Use judgement: the weight-based methods (mg/kg, BSA) '
                       'are more precise than the age estimate for this '
                       'patient.' % spread_pct)

        return {
            'usable_count': len(usable),
            'lowest': _round_dose(low),
            'highest': _round_dose(high),
            'spread_mg': _round_dose(high - low),
            'spread_pct': round(spread_pct, 1),
            'reference_method': reference['method'],
            'reference_dose': _round_dose(ref_dose),
            'agreement': agreement,
            'verdict': verdict,
            'daily_totals': [
                {
                    'method': f['method'],
                    'single': _round_dose(float(f['dose'])),
                    'daily': _round_dose(float(f['dose']) * float(doses_per_day or 1)),
                    'capped': f.get('capped', False),
                }
                for f in usable
            ],
            'doses': [_round_dose(d) for d in doses],
        }