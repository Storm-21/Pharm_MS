"""
Tests for the weight-based dosing formulas.

These assert the arithmetic against hand-worked values, because a dosing
calculation that is merely self-consistent is worthless - it has to match the
published formula. Each expected figure below is worked out longhand in the
comment beside it so the test can be checked without running it.
"""

import unittest

from app.services.weight_dosing_service import (
    DosingFormula,
    WeightDoser,
    KG_TO_LB,
)


class FakePatient:
    """A patient stub with only the attributes the doser reads."""

    def __init__(self, age=8, age_months=96, weight_kg=24.5, height_cm=132.0,
                 bsa_m2=None):
        self.age = age
        self.age_months = age_months
        self.weight_kg = weight_kg
        self.height_cm = height_cm
        self.bsa_m2 = bsa_m2 if bsa_m2 is not None else (
            DosingFormula.bsa_mosteller(height_cm, weight_kg)
            if weight_kg and height_cm else None
        )


class FormulaTests(unittest.TestCase):

    def test_weight_based(self):
        # 15 mg/kg x 24.5 kg = 367.5 mg
        self.assertAlmostEqual(DosingFormula.weight_based(15, 24.5), 367.5, places=6)

    def test_bsa_mosteller(self):
        # sqrt(132 x 24.5 / 3600) = sqrt(3234/3600) = 0.94780448... m^2
        self.assertAlmostEqual(
            DosingFormula.bsa_mosteller(132, 24.5), 0.94780, places=4)

    def test_clarks_rule(self):
        # 24.5 kg = 54.01 lb. 1000 mg x (54.01/150) = 360.09 mg
        # Checked against the definition: adult dose scaled by weight fraction
        # of a 150 lb adult.
        self.assertAlmostEqual(
            DosingFormula.clarks_rule(1000, 24.5), 360.09, places=1)

    def test_clarks_rule_at_reference_weight(self):
        # A 150 lb (68.04 kg) patient must receive exactly the adult dose.
        weight_kg = 150.0 / KG_TO_LB
        self.assertAlmostEqual(
            DosingFormula.clarks_rule(500, weight_kg), 500.0, places=6)

    def test_youngs_rule(self):
        # 1000 mg x 8 / (8 + 12) = 400 mg
        self.assertAlmostEqual(DosingFormula.youngs_rule(1000, 8), 400.0, places=6)

    def test_youngs_rule_at_12(self):
        # 1000 x 12/24 = 500 mg - the formula's own reference point.
        self.assertAlmostEqual(DosingFormula.youngs_rule(1000, 12), 500.0, places=6)


class RouteSelectionTests(unittest.TestCase):

    def test_mg_per_kg_preferred_when_weight_present(self):
        # Paracetamol: 15 mg/kg, ceiling 1000 mg.
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=24.5),
            {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
            doses_per_day=4,
        )
        self.assertEqual(result['route'], 'weight')
        self.assertTrue(result['is_weight_based'])
        self.assertEqual(result['dose'], 367.5)
        self.assertEqual(result['method'], 'Weight-based (mg/kg)')

    def test_clarks_rule_when_no_mg_per_kg(self):
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=24.5),
            {'adult_mg': 1000, 'mg_per_kg': None, 'max_mg': 1000},
        )
        self.assertEqual(result['route'], 'clark')
        self.assertTrue(result['is_weight_based'])
        self.assertEqual(result['confidence'], 'moderate')

    def test_youngs_rule_when_no_weight(self):
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=None, height_cm=None, bsa_m2=None),
            {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
        )
        self.assertEqual(result['route'], 'young')
        self.assertFalse(result['is_weight_based'])
        self.assertEqual(result['dose'], 400.0)
        self.assertTrue(any('No weight recorded' in w for w in result['warnings']))

    def test_bsa_route_only_when_requested(self):
        patient = FakePatient(age=40, weight_kg=70, height_cm=175)
        result = WeightDoser.calculate(
            patient,
            {'adult_mg': 100, 'dose_per_m2': 100},
            prefer_bsa=True,
            bsa_dose_per_m2=100,
        )
        self.assertEqual(result['route'], 'bsa')
        # sqrt(175 x 70 / 3600) = 1.84466... m^2; x100 = 184.47 mg.
        # The 100 mg adult reference must NOT cap this - a per-m2 dose is a
        # different quantity from an adult single dose.
        self.assertAlmostEqual(result['dose'], 184.47, places=1)
        self.assertFalse(result['capped'])


class SafetyTests(unittest.TestCase):

    def test_single_dose_cap_applied(self):
        # 200 mg/kg x 30 kg = 6000 mg, far above the 1000 mg ceiling.
        result = WeightDoser.calculate(
            FakePatient(age=10, weight_kg=30),
            {'adult_mg': 1000, 'mg_per_kg': 200, 'max_mg': 1000},
        )
        self.assertEqual(result['dose'], 1000)
        self.assertTrue(result['capped'])
        self.assertIn('single dose 1000 mg', result['caps_applied'])

    def test_daily_ceiling_reduces_single_dose(self):
        # 15 mg/kg x 40 kg = 600 mg, four times a day = 2400 mg/day, above the
        # 2000 mg/day ceiling, so the single dose is cut to 500 mg.
        result = WeightDoser.calculate(
            FakePatient(age=12, weight_kg=40),
            {'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 1000},
            doses_per_day=4,
            max_daily_dose_mg=2000,
        )
        self.assertEqual(result['dose'], 500)
        self.assertEqual(result['daily_total_mg'], 2000)
        self.assertTrue(result['capped'])

    def test_no_zero_dose_ever_returned(self):
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=0),
            {'adult_mg': 0, 'mg_per_kg': None, 'max_mg': None},
        )
        self.assertIsNone(result)

    def test_no_weight_is_never_assumed(self):
        # The critical safety property: a missing weight must not silently
        # default to an average adult and produce a weight-based dose.
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=None, height_cm=None, bsa_m2=None),
            {'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 500},
        )
        self.assertFalse(result['is_weight_based'])
        self.assertIn('No weight recorded', ' '.join(result['warnings']))

    def test_sub_milligram_precision_kept(self):
        # 0.0125 mg/kg x 5 kg = 0.0625 mg. Rounded to 3 dp this is 0.062 (0.0625
        # is not representable in binary float, so it rounds down). What matters
        # is that it is NOT collapsed to 0.06 by a blanket 2 dp round, which
        # would be a 4% error on a narrow-therapeutic-index drug.
        result = WeightDoser.calculate(
            FakePatient(age=0, age_months=6, weight_kg=5),
            {'adult_mg': 0.1, 'mg_per_kg': 0.0125, 'max_mg': 0.2},
        )
        self.assertAlmostEqual(result['dose'], 0.062, places=3)
        self.assertGreater(result['dose'], 0.06)

    def test_steps_are_reported(self):
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=24.5),
            {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
        )
        self.assertTrue(result['steps'])
        self.assertIn('24.5', ' '.join(result['steps']))

    def test_describe_is_readable(self):
        result = WeightDoser.calculate(
            FakePatient(age=8, weight_kg=24.5),
            {'adult_mg': 1000, 'mg_per_kg': 15, 'max_mg': 1000},
        )
        line = WeightDoser.describe(result)
        self.assertIn('367.5 mg', line)
        self.assertIn('Weight-based', line)


class ExplicitMethodTests(unittest.TestCase):
    """The prescriber may name the formula instead of taking the default.

    The bug these guard against: ``calculate`` set ``method = None`` while
    selecting its route, which overwrote the parameter of the same name before
    it was ever read. Every explicit choice was therefore silently ignored and
    the automatic route was used - a prescriber asking for Clark's rule got the
    mg/kg dose, with nothing on screen to say the request had been dropped.
    """

    def setUp(self):
        self.patient = FakePatient(age=8, weight_kg=24.5, height_cm=132)
        self.reference = {
            'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 1000,
        }

    def test_requested_method_is_honoured(self):
        result = WeightDoser.calculate(
            self.patient, self.reference, method='clark')
        self.assertEqual(result['route'], 'clark')
        self.assertIn("Clark's rule", result['method'])
        # Clark on a 24.5 kg child: 500 x (54.01 / 150) = 180.04 mg, which is
        # quite different from the 367.5 mg the mg/kg route gives. The point of
        # the test is that the number CHANGED, not merely the label.
        self.assertAlmostEqual(result['dose'], 180.04, places=1)

    def test_mg_per_kg_string_is_accepted(self):
        result = WeightDoser.calculate(
            self.patient, self.reference, method='mg/kg')
        self.assertEqual(result['route'], 'weight')

    def test_bsa_needs_a_per_m2_figure(self):
        # BSA selected but no per-m2 dose supplied: fall back, and say so.
        result = WeightDoser.calculate(
            self.patient, self.reference, method='bsa')
        self.assertNotEqual(result['route'], 'bsa')
        self.assertTrue(
            any('bsa' in w.lower() for w in result['warnings']),
            result['warnings'])

    def test_unknown_method_warns_instead_of_failing(self):
        result = WeightDoser.calculate(
            self.patient, self.reference, method='homeopathy')
        self.assertTrue(any('Unknown dose method' in w for w in result['warnings']))
        # It still returns a usable dose from the default route rather than
        # refusing to calculate at all.
        self.assertGreater(result['dose'], 0)

    def test_method_with_missing_inputs_explains_itself(self):
        # No weight on file, so Clark cannot be applied. The dose must still be
        # produced by a route that works, and the warning must say why.
        patient = FakePatient(age=8, weight_kg=None, height_cm=None)
        result = WeightDoser.calculate(patient, self.reference, method='clark')
        self.assertNotEqual(result['route'], 'clark')
        self.assertTrue(
            any('Clark' in w or 'clark' in w for w in result['warnings']),
            result['warnings'])


class AllFormulasTests(unittest.TestCase):
    """Every formula at once, for the choose-one-or-compare-all panel."""

    def setUp(self):
        self.patient = FakePatient(age=8, weight_kg=24.5, height_cm=132)
        self.reference = {
            'adult_mg': 500, 'mg_per_kg': 15, 'max_mg': 1000,
        }

    def test_every_formula_is_returned_even_when_unusable(self):
        # A formula that cannot be applied must still come back, flagged, with a
        # reason. Dropping it would leave the UI unable to explain why the
        # option is absent - which reads as a bug to the person using it.
        patient = FakePatient(age=8, weight_kg=None, height_cm=None)
        formulas = WeightDoser.all_formulas(patient, self.reference)
        self.assertEqual(len(formulas), len(WeightDoser.FORMULA_SPECS))
        for f in formulas:
            if not f['usable']:
                self.assertTrue(f['reason'], 'no reason given for %s' % f['key'])
                self.assertIsNone(f['dose'])

    def test_mg_per_kg_and_clark_are_both_computed(self):
        formulas = WeightDoser.all_formulas(self.patient, self.reference)
        by_key = {f['key']: f for f in formulas}
        self.assertTrue(by_key['mg/kg']['usable'])
        self.assertAlmostEqual(by_key['mg/kg']['dose'], 367.5, places=1)
        self.assertTrue(by_key['clark']['usable'])
        self.assertAlmostEqual(by_key['clark']['dose'], 180.04, places=1)

    def test_formula_without_a_reference_dose_is_disabled_with_a_reason(self):
        formulas = WeightDoser.all_formulas(self.patient, {})
        for f in formulas:
            self.assertFalse(f['usable'])
            self.assertTrue(f['reason'])

    def test_combine_reports_a_spread_not_an_average(self):
        # The combined view must never invent a midpoint: no published method
        # produces the average of two others, so presenting one would be
        # fabricating a dose.
        formulas = WeightDoser.all_formulas(self.patient, self.reference)
        combined = WeightDoser.combine(formulas, doses_per_day=3)
        self.assertGreaterEqual(combined['usable_count'], 2)
        self.assertAlmostEqual(combined['lowest'], 180.04, places=1)
        self.assertAlmostEqual(combined['highest'], 367.5, places=1)
        self.assertNotIn('average', combined['verdict'].lower())
        self.assertNotIn(
            round(sum(combined['doses']) / len(combined['doses']), 1),
            combined['doses'],
        )

    def test_one_formula_is_not_reported_as_agreement(self):
        # With no weight, only Young's rule applies. Saying it "agrees" would
        # present an age estimate as corroborated when nothing corroborated it.
        patient = FakePatient(age=8, weight_kg=None, height_cm=None)
        formulas = WeightDoser.all_formulas(patient, self.reference)
        combined = WeightDoser.combine(formulas, doses_per_day=3)
        self.assertEqual(combined['usable_count'], 1)
        self.assertEqual(combined['agreement'], 'single')
        self.assertIn('nothing to compare', combined['verdict'].lower())

    def test_nothing_usable_is_reported_plainly(self):
        combined = WeightDoser.combine(WeightDoser.all_formulas(
            FakePatient(age=8, weight_kg=None, height_cm=None), {}))
        self.assertEqual(combined['usable_count'], 0)
        self.assertIn('No formula', combined['summary'])

    def test_ceilings_are_applied_per_formula(self):
        # A comparison between a capped and an uncapped figure would be
        # meaningless, so each formula is capped independently.
        reference = {'adult_mg': 1000, 'mg_per_kg': 100, 'max_mg': 500}
        formulas = WeightDoser.all_formulas(self.patient, reference)
        for f in formulas:
            if f['usable']:
                self.assertLessEqual(f['dose'], 500)

    def test_high_doses_are_flagged_as_capped(self):
        reference = {'adult_mg': 1000, 'mg_per_kg': 100, 'max_mg': 500}
        formulas = WeightDoser.all_formulas(self.patient, reference)
        by_key = {f['key']: f for f in formulas}
        # 100 mg/kg x 24.5 kg = 2450 mg, well above the 500 mg ceiling.
        self.assertTrue(by_key['mg/kg']['capped'])
        self.assertTrue(by_key['mg/kg']['caps_applied'])


if __name__ == '__main__':
    unittest.main(verbosity=2)