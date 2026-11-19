# Production Planning Example

## Problem Description

A factory produces 3 products (A, B, C) using 2 machines (M1, M2).
The goal is to maximize total profit.

### Data

**Machine Time Requirements (hours per unit):**

|         | Machine 1 | Machine 2 |
|---------|-----------|-----------|
| Product A | 8        | 4         |
| Product B | 6        | 6         |
| Product C | 4        | 8         |

**Machine Availability:**
- Machine 1: 480 hours per month
- Machine 2: 380 hours per month

**Profit per Unit:**
- Product A: $50
- Product B: $60
- Product C: $45

## Objective

Maximize total profit by determining how many units of each product to manufacture, subject to:
- Machine time constraints
- Non-negative production quantities

## Expected Solution

This is a classic linear programming problem.
Expected maximum profit: approximately $3,300
