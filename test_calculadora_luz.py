import unittest

from calculadora_luz import calculate_split, make_receipt


class GeneralOtherPartyLabelsTest(unittest.TestCase):
    def test_calculation_and_receipt_use_other_party_label(self):
        result = calculate_split(100, 1000, 40, 200)

        self.assertIn("other_party_amount", result)
        self.assertIn("other_party_fixed_amount", result)
        self.assertEqual(result["other_party_amount"], 580)
        self.assertEqual(result["other_party_fixed_amount"], 100)

        record = {
            "date": "2026-06-07 12:00",
            "total_kwh": 100,
            "total_amount": 1000,
            "fixed_amount": 200,
            "my_kwh": 40,
            "result": result,
        }
        receipt = make_receipt(record)

        self.assertIn("Le corresponde pagar a la otra parte", receipt)
        self.assertIn("Parte del cargo fijo de la otra parte", receipt)
        self.assertNotIn("abuela", receipt.lower())

    def test_receipt_accepts_legacy_history_keys(self):
        record = {
            "date": "2026-05-31 21:43",
            "total_kwh": 404,
            "total_amount": 99656.32,
            "fixed_amount": 43289.37,
            "my_kwh": 154,
            "result": {
                "price_per_kwh": 139.52215346534655,
                "variable_amount": 56366.95,
                "my_variable_amount": 21486.411633663367,
                "my_fixed_amount": 21644.685,
                "grandmother_fixed_amount": 21644.685,
                "my_amount": 43131.09663366337,
                "grandmother_amount": 56525.223366336635,
            },
        }

        receipt = make_receipt(record)

        self.assertIn("Le corresponde pagar a la otra parte", receipt)
        self.assertIn("$56.525,22", receipt)
        self.assertNotIn("abuela", receipt.lower())


if __name__ == "__main__":
    unittest.main()
