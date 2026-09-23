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