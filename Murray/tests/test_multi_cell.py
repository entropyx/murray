import unittest
import pandas as pd
import numpy as np
from Murray.main import BetterGroups, transform_results_data
import tempfile
import os

class TestMultiCellFunctionality(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create sample data
        np.random.seed(42)
        locations = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        times = pd.date_range('2023-01-01', periods=30, freq='D')
        
        data = []
        for location in locations:
            for time in times:
                data.append({
                    'time': time,
                    'location': location,
                    'Y': np.random.poisson(100) + np.random.normal(0, 10)
                })
        
        self.data = pd.DataFrame(data)
        
        # Create correlation matrix
        pivot_data = self.data.pivot(index='time', columns='location', values='Y')
        self.correlation_matrix = pivot_data.corr()
        
    def test_better_groups_single_cell(self):
        """Test BetterGroups in single-cell mode (original functionality)"""
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50
        )
        
        self.assertIsNotNone(results)
        self.assertIsInstance(results, dict)
        
        # Check that each size has a single result (dict)
        for size, result in results.items():
            self.assertIsInstance(result, dict)
            self.assertIn('Best Treatment Group', result)
            self.assertIn('Control Group', result)
            self.assertIn('MAPE', result)
            self.assertIn('SMAPE', result)
    
    def test_better_groups_multi_cell(self):
        """Test BetterGroups in multi-cell mode"""
        multicell_config = {
            'sizes': [2, 3, 4],
            'top_n': 2
        }
        
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config
        )
        
        self.assertIsNotNone(results)
        self.assertIsInstance(results, dict)
        
        # Check that each size has a list of results
        for size, result_list in results.items():
            self.assertIsInstance(result_list, list)
            self.assertLessEqual(len(result_list), multicell_config['top_n'])
            
            # Check that results are ordered by MAPE (best first)
            if len(result_list) > 1:
                mape_values = [r['MAPE'] for r in result_list]
                self.assertEqual(mape_values, sorted(mape_values))
            
            # Check structure of each result
            for result in result_list:
                self.assertIn('Best Treatment Group', result)
                self.assertIn('Control Group', result)
                self.assertIn('MAPE', result)
                self.assertIn('SMAPE', result)
    
    def test_transform_results_data_single_cell(self):
        """Test transform_results_data with single-cell results"""
        # Create mock single-cell results
        mock_results = {
            2: {
                'Best Treatment Group': ['A', 'B'],
                'Control Group': ['C', 'D'],
                'MAPE': 0.05,
                'SMAPE': 0.06,
                'Actual Target Metric (y)': np.array([1, 2, 3]),
                'Predictions': np.array([1.1, 2.1, 3.1]),
                'Weights': np.array([0.5, 0.5]),
                'Holdout Percentage': 80.0
            }
        }
        
        transformed = transform_results_data(mock_results)
        
        self.assertIsInstance(transformed, dict)
        self.assertIn(2, transformed)
        
        result = transformed[2]
        self.assertIsInstance(result['Best Treatment Group'], str)
        self.assertIsInstance(result['Control Group'], str)
        self.assertIsInstance(result['MAPE'], float)
        self.assertIsInstance(result['SMAPE'], float)
    
    def test_transform_results_data_multi_cell(self):
        """Test transform_results_data with multi-cell results"""
        # Create mock multi-cell results
        mock_results = {
            2: [
                {
                    'Best Treatment Group': ['A', 'B'],
                    'Control Group': ['C', 'D'],
                    'MAPE': 0.05,
                    'SMAPE': 0.06,
                    'Actual Target Metric (y)': np.array([1, 2, 3]),
                    'Predictions': np.array([1.1, 2.1, 3.1]),
                    'Weights': np.array([0.5, 0.5]),
                    'Holdout Percentage': 80.0
                },
                {
                    'Best Treatment Group': ['A', 'C'],
                    'Control Group': ['B', 'D'],
                    'MAPE': 0.07,
                    'SMAPE': 0.08,
                    'Actual Target Metric (y)': np.array([1, 2, 3]),
                    'Predictions': np.array([1.2, 2.2, 3.2]),
                    'Weights': np.array([0.6, 0.4]),
                    'Holdout Percentage': 75.0
                }
            ]
        }
        
        transformed = transform_results_data(mock_results)
        
        self.assertIsInstance(transformed, dict)
        self.assertIn(2, transformed)
        
        # Should take the first (best) result
        result = transformed[2]
        self.assertEqual(result['MAPE'], 0.05)  # Best MAPE
        self.assertIsInstance(result['Best Treatment Group'], str)
        self.assertIsInstance(result['Control Group'], str)
    
    def test_multi_cell_config_validation(self):
        """Test that multi-cell config validation works"""
        # Test with invalid sizes
        multicell_config = {
            'sizes': [1, 100],  # Invalid sizes
            'top_n': 2
        }
        
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config
        )
        
        # Should handle invalid sizes gracefully
        self.assertIsNotNone(results)
    
    def test_empty_multi_cell_results(self):
        """Test handling of empty multi-cell results"""
        # Test with sizes that might not have results
        multicell_config = {
            'sizes': [1],  # Very small size
            'top_n': 2
        }
        
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config
        )
        
        # Should handle gracefully
        if results is not None:
            for size, result_list in results.items():
                self.assertIsInstance(result_list, list)
    
    def test_multi_cell_top_n_ordering(self):
        """Test that multi-cell results are properly ordered by MAPE"""
        multicell_config = {
            'sizes': [3],
            'top_n': 3
        }
        
        results = BetterGroups(
            similarity_matrix=self.correlation_matrix,
            excluded_locations=[],
            data=self.data,
            correlation_matrix=self.correlation_matrix,
            maximum_treatment_percentage=0.50,
            multicell_config=multicell_config
        )
        
        if results and 3 in results and len(results[3]) > 1:
            mape_values = [r['MAPE'] for r in results[3]]
            self.assertEqual(mape_values, sorted(mape_values))

if __name__ == '__main__':
    unittest.main() 