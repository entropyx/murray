import unittest
import pandas as pd
import numpy as np
from Murray.main import BetterGroups, transform_results_data
import tempfile
import os


class TestMultiCellFunctionality(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        np.random.seed(42)
        locations = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
        times = pd.date_range("2023-01-01", periods=30, freq="D")

        data = []
        for location in locations:
            for time in times:
                data.append(
                    {
                        "time": time,
                        "location": location,
                        "Y": np.random.poisson(100) + np.random.normal(0, 10),
                    }
                )

        self.data = pd.DataFrame(data)

        pivot_data = self.data.pivot(index="time", columns="location", values="Y")
        self.correlation_matrix = pivot_data.corr()

    def test_better_groups_single_cell(self):
        """Test BetterGroups in single-cell mode (original functionality)"""
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
        )

        self.assertIsNotNone(results)
        self.assertIsInstance(results, dict)

        for size, result in results.items():
            self.assertIsInstance(result, dict)
            self.assertIn("Best Treatment Group", result)
            self.assertIn("Control Group", result)
            self.assertIn("MAPE", result)
            self.assertIn("SMAPE", result)

    def test_better_groups_multi_cell(self):
        """Test BetterGroups in multi-cell mode"""
        multicell_config = {"sizes": [2, 3, 4], "top_n": 2}

        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config,
        )

        self.assertIsNotNone(results)
        self.assertIsInstance(results, dict)

        for size, result_list in results.items():
            self.assertIsInstance(result_list, list)
            self.assertLessEqual(len(result_list), multicell_config["top_n"])

            if len(result_list) > 1:
                mape_values = [r["MAPE"] for r in result_list]
                self.assertEqual(mape_values, sorted(mape_values))

            for result in result_list:
                self.assertIn("Best Treatment Group", result)
                self.assertIn("Control Group", result)
                self.assertIn("MAPE", result)
                self.assertIn("SMAPE", result)

    def test_transform_results_data_single_cell(self):
        """Test transform_results_data with single-cell results"""
        mock_results = {
            2: {
                "Best Treatment Group": ["A", "B"],
                "Control Group": ["C", "D"],
                "MAPE": 0.05,
                "SMAPE": 0.06,
                "Actual Target Metric (y)": np.array([1, 2, 3]),
                "Predictions": np.array([1.1, 2.1, 3.1]),
                "Weights": np.array([0.5, 0.5]),
                "Holdout Percentage": 80.0,
            }
        }

        transformed = transform_results_data(mock_results)

        self.assertIsInstance(transformed, dict)
        self.assertIn(2, transformed)

        result = transformed[2]
        self.assertIsInstance(result["Best Treatment Group"], str)
        self.assertIsInstance(result["Control Group"], str)
        self.assertIsInstance(result["MAPE"], float)
        self.assertIsInstance(result["SMAPE"], float)

    def test_transform_results_data_multi_cell(self):
        """Test transform_results_data with multi-cell results"""
        mock_results = {
            2: [
                {
                    "Best Treatment Group": ["A", "B"],
                    "Control Group": ["C", "D"],
                    "MAPE": 0.05,
                    "SMAPE": 0.06,
                    "Actual Target Metric (y)": np.array([1, 2, 3]),
                    "Predictions": np.array([1.1, 2.1, 3.1]),
                    "Weights": np.array([0.5, 0.5]),
                    "Holdout Percentage": 80.0,
                },
                {
                    "Best Treatment Group": ["A", "C"],
                    "Control Group": ["B", "D"],
                    "MAPE": 0.07,
                    "SMAPE": 0.08,
                    "Actual Target Metric (y)": np.array([1, 2, 3]),
                    "Predictions": np.array([1.2, 2.2, 3.2]),
                    "Weights": np.array([0.6, 0.4]),
                    "Holdout Percentage": 75.0,
                },
            ]
        }

        transformed = transform_results_data(mock_results)

        self.assertIsInstance(transformed, dict)
        self.assertIn(2, transformed)

        result = transformed[2]
        self.assertEqual(result["MAPE"], 0.05)
        self.assertIsInstance(result["Best Treatment Group"], str)
        self.assertIsInstance(result["Control Group"], str)

    def test_multi_cell_config_validation(self):
        """Test that multi-cell config validation works"""
        multicell_config = {"sizes": [1, 100], "top_n": 2}

        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config,
        )

        self.assertIsNotNone(results)

    def test_empty_multi_cell_results(self):
        """Test handling of empty multi-cell results"""
        multicell_config = {"sizes": [1], "top_n": 2}

        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config,
        )

        if results is not None:
            for size, result_list in results.items():
                self.assertIsInstance(result_list, list)

    def test_multi_cell_top_n_ordering(self):
        """Test that multi-cell results are properly ordered by MAPE"""
        multicell_config = {"sizes": [3], "top_n": 3}

        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config,
        )

        if results and 3 in results and len(results[3]) > 1:
            mape_values = [r["MAPE"] for r in results[3]]
            self.assertEqual(mape_values, sorted(mape_values))

    def test_partition_is_disjoint_balanced_deterministic(self):
        from Murray.main import partition_locations_systematic

        part_a = partition_locations_systematic(self.data, [], k=3, seed=42)
        part_b = partition_locations_systematic(self.data, [], k=3, seed=42)

        # deterministic
        self.assertEqual(part_a, part_b)
        # three non-empty cells
        self.assertEqual(len(part_a), 3)
        # disjoint and full coverage of the 10 locations
        all_locs = [loc for locs in part_a.values() for loc in locs]
        self.assertEqual(sorted(all_locs), sorted(self.data["location"].unique()))
        self.assertEqual(len(all_locs), len(set(all_locs)))  # no overlap
        # balanced: cell sizes differ by at most 1
        sizes = sorted(len(v) for v in part_a.values())
        self.assertLessEqual(sizes[-1] - sizes[0], 1)

    def test_partition_caps_k_at_available_and_respects_exclusions(self):
        from Murray.main import partition_locations_systematic

        part = partition_locations_systematic(self.data, ["A", "B"], k=20, seed=42)
        all_locs = [loc for locs in part.values() for loc in locs]
        self.assertNotIn("A", all_locs)
        self.assertNotIn("B", all_locs)
        # only 8 locations remain, so at most 8 cells
        self.assertLessEqual(len(part), 8)
        self.assertEqual(sorted(all_locs), sorted(set(self.data["location"].unique()) - {"A", "B"}))

    def test_select_treatments_restricted_to_slice(self):
        from Murray.main import select_treatments_exclusive

        slice_locs = ["A", "B", "C"]
        groups = select_treatments_exclusive(
            self.correlation_matrix, treatment_size=2, excluded_locations=[],
            allowed_locations=slice_locs, seed=42,
        )
        # every returned treatment is fully inside the slice
        for g in groups:
            self.assertTrue(set(g).issubset(set(slice_locs)))
        # exhaustive for a tiny pool: C(3,2) == 3 unique combos
        self.assertEqual(len(groups), 3)

    def test_select_treatments_deterministic(self):
        from Murray.main import select_treatments_exclusive

        a = select_treatments_exclusive(
            self.correlation_matrix, 2, [], allowed_locations=["A", "B", "C", "D"], seed=7,
        )
        b = select_treatments_exclusive(
            self.correlation_matrix, 2, [], allowed_locations=["A", "B", "C", "D"], seed=7,
        )
        self.assertEqual(sorted(map(sorted, a)), sorted(map(sorted, b)))

    def test_resolve_feasibility_reduces_k_when_too_many_cells(self):
        from Murray.main import _resolve_multicell_feasibility

        # 10 locations, min size 3 -> at most 3 cells
        eff_k, warnings = _resolve_multicell_feasibility(
            allowed_sizes=[3], total_cells_needed=5, excluded_locations=[], data=self.data,
        )
        self.assertEqual(eff_k, 3)
        self.assertTrue(warnings)

    def test_resolve_feasibility_unchanged_when_feasible(self):
        from Murray.main import _resolve_multicell_feasibility

        eff_k, warnings = _resolve_multicell_feasibility(
            allowed_sizes=[2], total_cells_needed=3, excluded_locations=[], data=self.data,
        )
        self.assertEqual(eff_k, 3)
        self.assertEqual(warnings, [])

    def test_finalize_controls_disjoint_and_scored(self):
        from Murray.main import _finalize_multicell_controls

        df_pivot = self.data.pivot(index="time", columns="location", values="Y")
        total_Y = self.data["Y"].sum()
        chosen = [(["A", "B"], 2), (["C", "D"], 2)]
        all_treatments = {"A", "B", "C", "D"}

        cells = _finalize_multicell_controls(
            chosen, all_treatments, self.data, total_Y, self.correlation_matrix,
            min_holdout=50.0, df_pivot=df_pivot, excluded_locations=[],
            excluded_control_locations=None,
        )

        self.assertEqual(len(cells), 2)
        for idx, cell in enumerate(cells):
            self.assertEqual(cell["Cell"], idx + 1)
            self.assertIn("Size", cell)
            self.assertIn("MAPE", cell)
            self.assertIn("Holdout Percentage", cell)
            # no treatment leaked into any cell's control
            self.assertFalse(set(cell["Control Group"]) & all_treatments)


    def _run_global(self, sizes, top_n, excluded=None):
        return BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=excluded or [],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config={"sizes": sizes, "top_n": top_n},
            global_optimization=True,
        )

    def test_global_multicell_contract_and_disjoint(self):
        results = self._run_global(sizes=[2, 3], top_n=3)
        self.assertIsNotNone(results)
        self.assertIn("global_experiment", results)
        cells = results["global_experiment"]
        self.assertGreaterEqual(len(cells), 1)

        seen = set()
        for cell in cells:
            for key in ("Cell", "Size", "Best Treatment Group", "Control Group",
                        "MAPE", "SMAPE", "Holdout Percentage",
                        "Actual Target Metric (y)", "Predictions", "Weights",
                        "observed_conformity"):
                self.assertIn(key, cell)
            tg = set(cell["Best Treatment Group"])
            self.assertFalse(tg & seen, "treatment groups overlap across cells")
            seen |= tg

    def test_global_multicell_deterministic(self):
        a = self._run_global(sizes=[2, 3], top_n=3)["global_experiment"]
        b = self._run_global(sizes=[2, 3], top_n=3)["global_experiment"]
        self.assertEqual(
            [(c["Size"], sorted(c["Best Treatment Group"])) for c in a],
            [(c["Size"], sorted(c["Best Treatment Group"])) for c in b],
        )

    def test_global_multicell_robust_when_k_too_large(self):
        # 10 locations, size 3, ask for 9 cells -> reduced, not None/raising
        results = self._run_global(sizes=[3], top_n=9)
        self.assertIsNotNone(results)
        cells = results["global_experiment"]
        self.assertGreaterEqual(len(cells), 1)
        self.assertLessEqual(len(cells), 3)

    def test_global_multicell_scoring_consistency(self):
        from Murray.main import evaluate_group_exclusive

        results = self._run_global(sizes=[2], top_n=2)
        cells = results["global_experiment"]
        all_treatments = set()
        for c in cells:
            all_treatments |= set(c["Best Treatment Group"])

        df_pivot = self.data.pivot(index="time", columns="location", values="Y")
        total_Y = self.data["Y"].sum()
        for c in cells:
            tg = c["Best Treatment Group"]
            res = evaluate_group_exclusive(
                tg, self.data, total_Y, self.correlation_matrix, 50.0, df_pivot,
                used_treatment_locations=all_treatments - set(tg),
                excluded_locations=[], excluded_control_locations=None,
            )
            self.assertEqual(c["MAPE"], res[2])  # reported MAPE matches the final control

    def test_results_by_cell_for_sensitivity_keys_each_cell_separately(self):
        from Murray.main import _results_by_cell_for_sensitivity

        # Two cells of the SAME size (8) but different treatment groups.
        global_experiment = [
            {"Cell": 1, "Size": 8, "Best Treatment Group": ["a"], "Control Group": ["c"],
             "MAPE": 1.0, "SMAPE": 2.0, "Actual Target Metric (y)": [1], "Predictions": [1],
             "Weights": [1], "observed_conformity": 0.0},
            {"Cell": 2, "Size": 8, "Best Treatment Group": ["b"], "Control Group": ["d"],
             "MAPE": 1.1, "SMAPE": 2.1, "Actual Target Metric (y)": [2], "Predictions": [2],
             "Weights": [1], "observed_conformity": 0.0},
        ]
        by_cell = _results_by_cell_for_sensitivity(global_experiment)

        # Keyed by cell number, not size -> two distinct entries (no collision).
        self.assertEqual(sorted(by_cell.keys()), [1, 2])
        self.assertEqual(by_cell[1]["Best Treatment Group"], ["a"])
        self.assertEqual(by_cell[2]["Best Treatment Group"], ["b"])

    def test_cell_rank_key_prefers_lower_scaled_l2_then_smape(self):
        from Murray.main import _cell_rank_key

        # evaluate_group_exclusive tuple layout: (.., MAPE=2, SMAPE=3, .., scaled_l2=8, ..)
        def res(scaled_l2, smape, mape):
            return ("t", "c", mape, smape, None, None, None, None, scaled_l2, None)

        # Lower scaled-L2 imbalance wins, even when its MAPE is much worse.
        better_fit = res(scaled_l2=0.05, smape=9.0, mape=9.0)
        worse_fit = res(scaled_l2=0.10, smape=9.0, mape=1.0)
        self.assertLess(_cell_rank_key(better_fit), _cell_rank_key(worse_fit))

        # Tie on scaled-L2 -> lower SMAPE is the tiebreak.
        low_smape = res(scaled_l2=0.05, smape=4.0, mape=9.0)
        self.assertLess(_cell_rank_key(low_smape), _cell_rank_key(better_fit))


if __name__ == "__main__":
    unittest.main()
