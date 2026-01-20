# Transportation Problem Example

## Problem Description

A company needs to ship products from 3 warehouses to 4 stores at minimum cost.

### Data

**Warehouse Supplies (units available):**
- Warehouse A: 100 units
- Warehouse B: 150 units  
- Warehouse C: 200 units

**Store Demands (units needed):**
- Store 1: 80 units
- Store 2: 120 units
- Store 3: 90 units
- Store 4: 110 units

**Transportation Costs ($ per unit):**

|         | Store 1 | Store 2 | Store 3 | Store 4 |
|---------|---------|---------|---------|---------|
| Whse A  | 5       | 8       | 6       | 7       |
| Whse B  | 6       | 7       | 9       | 5       |
| Whse C  | 8       | 6       | 7       | 9       |

## Objective

Minimize the total transportation cost while:
- Meeting all store demands
- Not exceeding warehouse supplies

## Expected Solution

The optimal solution should allocate shipments to minimize total cost.
Expected objective value: approximately $2,540
