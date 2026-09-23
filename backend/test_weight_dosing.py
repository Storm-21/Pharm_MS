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


if __name__ == '__main__':
    unittest.main(verbosity=2)