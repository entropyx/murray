# Feature: Add a new "Power Analysis" page

## Objective
Create a new page in the Streamlit application that allows users to perform a power analysis to determine the required sample size for their experiment.

## Requirements
- [ ] A new page named "Power Analysis" should be added to the Streamlit navigation.
- [ ] The page should allow users to upload their data.
- [ ] The user should be able to specify the desired Minimum Detectable Effect (MDE), and the treatment period.
- [ ] The page should display the minimum required sample size to achieve a statistical power of 80%.

## Acceptance Criteria
- [ ] The "Power Analysis" page is accessible from the main navigation.
- [ ] Users can upload a CSV file with their data.
- [ ] The page correctly calculates and displays the minimum required sample size.

## Technical Notes
- A new function `calculate_minimum_sample_size` will be needed in `Murray/main.py`.
- A new Streamlit page `power_analysis.py` will need to be created.
- The `app.py` file will need to be updated to include the new page in the navigation.

## Progress
- [ ] Planning
- [ ] Implementation
- [ ] Testing
- [ ] Documentation
- [ ] Deployment

Last updated: 2025-07-15 by Gemini
