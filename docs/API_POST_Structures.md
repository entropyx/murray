# API POST Request Structures

This document outlines the structure for the main POST requests to the Murray API.

## 1. Experimental Design: Single-Cell Mode

This request submits a standard design analysis task.

**Endpoint:** `POST /analyze/design`

**Request Body:** `multipart/form-data`

| Field | Type | Description | Example Value |
| --- | --- | --- | --- |
| `file` | File | The CSV file with the data for the analysis. | `data.csv` |
| `date_column` | String | The name of the column with the date. | `date` |
| `location_column` | String | The name of the column with the location. | `market` |
| `target_column` | String | The name of the column with the target variable. | `revenue` |
| `excluded_locations` | String | A comma-separated list of locations to exclude. | `loc1,loc2` |
| `maximum_treatment_percentage` | Float | The maximum percentage of locations that can be in the treatment group. | `0.3` |
| `significance_level` | Float | The significance level for the analysis. | `0.1` |
| `deltas_range` | String | A comma-separated string with the start, stop, and step for the deltas range. | `0.01,0.1,0.01` |
| `periods_range` | String | A comma-separated string with the start, stop, and step for the periods range. | `5,15,5` |
| `webhook` | String | (Optional) The URL for webhook notifications. | `https://...` |
| `enable_multicell` | Boolean | Must be `False` or omitted for single-cell mode. | `False` |

---

## 2. Experimental Design: Multi-Cell Mode

This request submits a design analysis task that creates a globally optimized experiment with multiple cells of varying sizes.

**Endpoint:** `POST /analyze/design`

**Request Body:** `multipart/form-data`

| Field | Type | Description | Example Value |
| --- | --- | --- | --- |
| `file` | File | The CSV file with the data for the analysis. | `data.csv` |
| `date_column` | String | The name of the column with the date. | `date` |
| `location_column` | String | The name of the column with the location. | `market` |
| `target_column` | String | The name of the column with the target variable. | `revenue` |
| `excluded_locations` | String | A comma-separated list of locations to exclude. | `loc1,loc2` |
| `maximum_treatment_percentage` | Float | The maximum percentage of locations that can be in the treatment group. | `0.3` |
| `significance_level` | Float | The significance level for the analysis. | `0.1` |
| `deltas_range` | String | A comma-separated string with the start, stop, and step for the deltas range. | `0.01,0.1,0.01` |
| `periods_range` | String | A comma-separated string with the start, stop, and step for the periods range. | `5,15,5` |
| `webhook` | String | (Optional) The URL for webhook notifications. | `https://...` |
| `enable_multicell` | Boolean | **Must be `True` to enable multi-cell mode.** | `True` |
| `multicell_sizes` | String | **Required for multi-cell.** A comma-separated list of allowed cell sizes. | `2,3,4` |
| `multicell_cells_count` | Integer | **Required for multi-cell.** The total number of cells in the final experiment. | `3` |

---

## 3. Experimental Evaluation

This request submits an evaluation analysis task for a completed experiment.

**Endpoint:** `POST /analyze/evaluation`

**Request Body:** `multipart/form-data`

| Field | Type | Description | Example Value |
| --- | --- | --- | --- |
| `file` | File | The CSV file with the data for the analysis. | `data.csv` |
| `date_column` | String | The name of the column with the date. | `date` |
| `location_column` | String | The name of the column with the location. | `market` |
| `target_column` | String | The name of the column with the target variable. | `revenue` |
| `treatment_start_date` | String | The start date of the treatment period (YYYY-MM-DD). | `2023-01-01` |
| `treatment_end_date` | String | The end date of the treatment period (YYYY-MM-DD). | `2023-01-31` |
| `treatment_group` | String | A comma-separated list of locations in the treatment group. | `locA,locB,locC` |
| `spend` | Float | The spend for the treatment. | `10000.50` |
| `mmm_option` | String | The MMM option to use for the analysis. | `option_1` |
| `webhook` | String | (Optional) The URL for webhook notifications. | `https://...` |