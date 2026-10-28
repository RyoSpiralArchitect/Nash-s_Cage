import unittest

from analyze import collapse_fema, date, days, quantile, stats, world_bank, INDICATORS


class AuditTests(unittest.TestCase):
    def row(self, **updates):
        return {"id": "one", "femaDeclarationString": "DR-1-X", "disasterNumber": 1,
                "state": "X", "declarationType": "DR", "declarationDate": "2000-01-02T00:00:00Z",
                "declarationRequestDate": "2000-01-01T00:00:00Z", "incidentBeginDate": "2000-01-01T00:00:00Z",
                "incidentType": "Flood", "tribalRequest": False, **updates}

    def test_collapse_area_rows_not_independent_declarations(self):
        rows = collapse_fema([self.row(), self.row(id="two")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["designated_area_rows"], 2)

    def test_conflict_rejected(self):
        with self.assertRaises(ValueError):
            collapse_fema([self.row(), self.row(id="two", declarationRequestDate=None)])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            collapse_fema([self.row(), self.row()])

    def test_missing_is_not_zero(self):
        result = stats([None, 0, 5])
        self.assertEqual(result["n_missing"], 1)
        self.assertEqual(result["n_zero"], 1)
        self.assertEqual(result["median"], 2.5)
        self.assertIsNone(stats([None])["median"])

    def test_negative_lag_retained(self):
        row = collapse_fema([self.row(incidentBeginDate="2000-01-03T00:00:00Z")])[0]
        self.assertEqual(row["begin_to_declaration_days"], -1)
        self.assertEqual(row["begin_to_request_days"], -2)

    def test_quantile_rule(self):
        self.assertEqual(quantile([0, 10, 20, 30], .25), 7.5)
        self.assertEqual(quantile([7], .9), 7)
        self.assertIsNone(quantile([], .5))

    def test_calendar_not_hour_difference(self):
        self.assertEqual(days("2000-01-01T23:00:00Z", "2000-01-02T01:00:00Z"), 1)
        self.assertEqual(str(date("2000-01-02T01:00:00+09:00")), "2000-01-01")

    def test_cohort_boundary(self):
        with self.assertRaises(ValueError):
            collapse_fema([self.row(declarationDate="2025-01-01T00:00:00Z")])

    def test_world_bank_missing_and_duplicate(self):
        data = {}
        for indicator in INDICATORS:
            rows = [{"countryiso3code": c, "date": str(y), "indicator": {"id": indicator},
                     "value": None if y == 2000 else 10} for c in ("BGD", "KEN") for y in range(2000, 2025)]
            data[indicator] = [{"pages": 1, "total": 50}, rows]
        cells, summary = world_bank(data)
        self.assertEqual(len(cells), 100)
        self.assertEqual(summary[0]["n_observed"], 4)
        self.assertEqual(summary[0]["mean_annual_ratio_pct"], 10)
        data[INDICATORS[0]][1][0] = data[INDICATORS[0]][1][1]
        with self.assertRaises(ValueError):
            world_bank(data)


if __name__ == "__main__":
    unittest.main()
