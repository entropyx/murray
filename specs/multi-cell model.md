# Feature: Multi-Cell Experimental Design with Heterogeneous Cell Sizes

## Objective
To enhance the multi-cell design functionality by allowing the creation of a single, globally optimized experiment composed of cells with varying sizes. This provides greater flexibility and increases the potential for finding a more powerful and efficient experimental design.

---

## 1. Current Behavior (As-Is)

Currently, the system treats the "Select Group Sizes" input as a list of separate tasks. It generates a distinct multi-cell experiment for **each** size provided.

**Example:**
-   **User Input:**
    -   `Select Group Sizes`: `[2, 3, 4]`
    -   `Top N (Number of Cells)`: `3`
-   **Current Output:** The system generates **three separate experiments**:
    1.  **Experiment A:** A 3-cell experiment where every treatment group has a size of **2**.
    2.  **Experiment B:** A 3-cell experiment where every treatment group has a size of **3**.
    3.  **Experiment C:** A 3-cell experiment where every treatment group has a size of **4**.

The key limitation is that all cells within a single experiment must have the same size.

---

## 2. Proposed Behavior (To-Be)

The proposed change is to generate a **single, globally optimized experiment** where the cell sizes can be heterogeneous. The user inputs will now have a new meaning:

-   `Top N`: Defines the **total number of cells** in the final, single experiment.
-   `Select Group Sizes`: Defines a **pool of allowed sizes** from which the model can choose for each cell.

The model's new objective is to find the best combination of `N` treatment groups (and their corresponding controls) from the entire universe of possibilities, adhering to the allowed sizes and ensuring all locations are mutually exclusive across the entire experiment.

**Example:**
-   **User Input:**
    -   `Allowed Group Sizes`: `[2, 3, 4]`
    -   `Top N (Total Cells)`: `3`
-   **Proposed Output:** The system generates **one single experiment** with 3 cells. The model might determine the optimal design is:
    -   **Cell 1:** A treatment group of size **2**.
    -   **Cell 2:** A treatment group of size **4**.
    -   **Cell 3:** A treatment group of size **3**.

The final combination of sizes is determined by the optimization algorithm seeking the best overall performance (e.g., lowest aggregate MAPE/SMAPE) across all `N` cells.

---

## 3. Key Changes to Logic

1.  **Input Interpretation:** The `Select Group Sizes` array is no longer a list of jobs to run, but a constraint (a list of valid sizes) for a single, larger optimization problem.
2.  **Candidate Pool Generation:** The system must first find the best individual candidate groups for *all* allowed sizes.
3.  **Global Optimization:** A new optimization layer is required. After finding the best individual groups, the model must select the best **combination** of `N` groups that are mutually exclusive. This means if a location is used in the treatment or control of Cell 1, it cannot be used anywhere in Cell 2, Cell 3, etc.
4.  **Mutual Exclusivity:** The constraint that all locations (both treatment and control) must be unique now applies **globally across all cells** in the single experiment.

---

## 4. User Interface (UI) Impact

-   The label "Select Group Sizes" should be updated to **"Allowed Group Sizes"** or **"Possible Group Sizes"** to reflect its new meaning.
-   The description below the input should clarify that the model will create a single experiment with cells of potentially different sizes from this list.

---

## 5. Acceptance Criteria

1.  The system must generate only **one** experimental design, not one per size.
2.  The total number of cells in the output must exactly match the `Top N` input.
3.  The size of each cell in the final design must be one of the sizes provided in the "Allowed Group Sizes" list.
4.  A comprehensive list of all treatment and control locations across **all** cells in the final experiment must contain no duplicate locations.
5.  The model should select a combination of cells that is demonstrably optimal based on the chosen evaluation metric (e.g., minimizing the sum of MAPE across all cells).

---

## 6. Progress

- [ ] Planning
- [ ] Implementation
- [ ] Testing
- [ ] Documentation
- [ ] Deployment

*Last updated: 2025-07-15 by Gemini*
