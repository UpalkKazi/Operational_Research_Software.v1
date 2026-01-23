# OR Assistant User Guide

## Introduction

OR Assistant is an AI-powered tool that helps solve Operations Research problems using natural language. Instead of manually formulating mathematical models, you can describe your problem in plain English and get solutions automatically.

OR Assistant supports multiple AI providers:
- **Anthropic Claude**: High-quality reasoning and analysis
- **OpenAI**: GPT-4o, GPT-4 Turbo, and other models

You can use either provider - the tool will automatically detect which API key you have configured, or you can explicitly choose a provider.

## Getting Started

### Installation

See the main [README.md](../README.md) for installation instructions.

### Quick Start

1. **Start the app**:
   ```bash
   streamlit run app.py
   ```

2. **Describe your problem** in the text area

3. **Click "Solve Problem"**

4. **Review results** in the tabs

## Supported Problem Types

### Linear Programming (LP)

**What it is**: Optimization with linear objective and constraints

**When to use**: 
- Production planning
- Resource allocation
- Diet optimization
- Portfolio optimization

**Example**:
```
Maximize profit from producing products A and B.
Product A earns $50 profit, uses 8 hours of labor
Product B earns $60 profit, uses 6 hours of labor
Available labor: 480 hours
Available material: 200 units
Product A needs 4 units material, Product B needs 6 units
```

### Integer Programming (IP)

**What it is**: LP with integer (whole number) variables

**When to use**:
- Facility location
- Capital budgeting
- Staff scheduling
- Yes/no decisions

**Example**:
```
Select projects to maximize NPV with budget constraint.
Project A: NPV $100k, cost $50k
Project B: NPV $150k, cost $80k
Project C: NPV $90k, cost $40k
Budget: $120k
Each project either selected (1) or not (0)
```

### Transportation Problem

**What it is**: Minimize cost of shipping goods from sources to destinations

**When to use**:
- Supply chain optimization
- Distribution planning
- Warehouse management

**Example**:
```
Ship products from 3 warehouses to 4 stores at minimum cost.
Warehouse capacities: [100, 150, 200] units
Store demands: [80, 120, 90, 110] units
Shipping costs: [provide cost matrix]
```

### Assignment Problem

**What it is**: Optimally match resources to tasks

**When to use**:
- Task assignment
- Machine scheduling
- Resource matching

**Example**:
```
Assign 4 workers to 4 tasks to minimize total time.
Time matrix (worker x task):
[[5, 8, 6, 7],
 [6, 7, 9, 5],
 [8, 6, 7, 9],
 [7, 8, 8, 6]]
```

### Scheduling

**What it is**: Sequence tasks over time

**When to use**:
- Production scheduling
- Job shop scheduling
- Project planning

**Example**:
```
Schedule 5 jobs on 3 machines to minimize completion time.
Job durations: [provide processing times]
Precedence constraints: [specify order requirements]
```

## How to Describe Problems

### Be Specific

✅ Good:
```
I have 3 warehouses with capacities 100, 150, and 200 units.
I need to ship to 4 stores requiring 80, 120, 90, and 110 units.
Shipping costs per unit are: [cost matrix]
Minimize total shipping cost.
```

❌ Vague:
```
I need to optimize shipping
```

### Include All Data

Make sure to specify:
- **Objective**: What to minimize or maximize
- **Decision variables**: What you're deciding
- **Constraints**: Limitations and requirements
- **Parameters**: All numbers (capacities, costs, demands, etc.)

### Use Clear Language

- State objective clearly: "minimize cost", "maximize profit"
- Identify constraints: "cannot exceed", "must be at least"
- Provide units: "dollars", "hours", "units"

## Understanding Results

### Solution Status

- **Optimal**: Best solution found ✅
- **Infeasible**: No solution exists - check constraints
- **Unbounded**: Problem can improve infinitely - add bounds
- **Time Limit**: Didn't finish in time - increase limit or simplify

### Key Metrics

- **Objective Value**: The optimal cost/profit/value
- **Solve Time**: How long it took to solve
- **Variables**: The decision values
- **Binding Constraints**: Tight limits that affect the solution

### Interpreting Variable Values

Variables show your optimal decisions:
- Production quantities
- Shipment amounts
- Resource allocations
- Binary choices (0 or 1)

### Sensitivity Analysis

Shows how sensitive the solution is to changes:
- **Shadow Prices**: Value of relaxing a constraint
- **Reduced Costs**: How much to change before a variable enters solution
- **Ranges**: How much parameters can change while staying optimal

## Advanced Features

### Solver Selection

Choose different solvers based on problem type:
- **PuLP (CBC)**: Good for most LP/IP problems
- **OR-Tools**: Excellent for routing and constraint programming
- **CVXPY**: Best for convex optimization
- **Gurobi/CPLEX**: Commercial solvers for large problems

### Time Limits

Set maximum solve time:
- Small problems: 10-30 seconds
- Medium problems: 1-5 minutes
- Large problems: 5-30 minutes

### Export Results

Download results in various formats:
- CSV: Variable values
- JSON: Complete solution data
- PDF: Formatted report

## Tips for Best Results

1. **Start simple**: Test with small examples first
2. **Check data**: Verify all numbers are correct
3. **Review formulation**: Make sure problem makes sense
4. **Validate results**: Do the answers seem reasonable?
5. **Iterate**: Refine based on initial results

## Common Issues

### "Infeasible" Result

**Causes**:
- Contradictory constraints
- Impossible requirements
- Data errors

**Solutions**:
- Review constraints
- Check if demands exceed supply
- Relax some requirements

### "Unbounded" Result

**Causes**:
- Missing upper bounds
- Incomplete constraints
- Wrong objective direction

**Solutions**:
- Add bounds to variables
- Add missing constraints
- Verify objective function

### Slow Solving

**Causes**:
- Large problem size
- Integer variables
- Complex constraints

**Solutions**:
- Use commercial solver (Gurobi/CPLEX)
- Increase time limit
- Simplify problem
- Add valid inequalities

## Getting Help

- Check [examples](../data/examples/)
- Review [API documentation](API_REFERENCE.md)
- Open an issue on GitHub
- Use the CLI help: `python cli.py --help`

## Next Steps

- Try the example problems
- Create your own problems
- Explore advanced features
- Contribute improvements
