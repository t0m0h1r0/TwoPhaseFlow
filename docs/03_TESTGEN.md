# TEST GENERATION PROTOCOL

All numerical algorithms must have validation tests.

Tests must verify:

1. convergence order
2. conservation properties
3. numerical stability

---

# Test Types

### Order of Accuracy

Use analytic functions such as:

sin(2πx)  
cos(2πx)

Check convergence:

O(h²)  
O(h⁴)  
O(h⁶)

---

### Physical Properties

Verify:

- divergence-free velocity
- mass conservation
- symmetry

---

# Test Requirements

Each new module must include:

- at least one accuracy test
- at least one property test

Tests must be placed in:


src/twophase/tests/


---

# Output Format

1. Explain what the test verifies
2. Provide pytest code