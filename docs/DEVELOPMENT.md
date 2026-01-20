# OR Assistant Development Guide

## For Undergraduate CS Students

This guide helps you build the OR Assistant system step-by-step.

## Project Structure

```
or-assistant/
├── src/                    # Source code
│   ├── agents/            # AI classification
│   ├── modeling/          # Model generation
│   ├── solvers/           # Solver interfaces
│   ├── interpreters/      # Result explanation
│   ├── simulation/        # Future: simulation
│   └── utils/             # Utilities
├── tests/                 # Test files
├── data/                  # Examples & templates
├── docs/                  # Documentation
├── app.py                 # Streamlit UI
└── cli.py                 # Command line
```

## Development Timeline (12 Weeks)

### Week 1-2: Setup & Learning
**Goal**: Get environment working, understand basics

**Tasks**:
1. Install Python 3.10+ and dependencies
2. Get Anthropic API key
3. Complete PuLP tutorials
4. Run example problems
5. Test basic Streamlit app

**Deliverable**: "Hello World" app that calls Claude

### Week 3-4: Problem Classification
**Goal**: Build AI agent that understands problems

**Tasks**:
1. Study `src/agents/problem_classifier.py`
2. Test with example problems
3. Add more problem types if needed
4. Write tests
5. Debug classification issues

**Deliverable**: Classifier that works for 5+ problem types

### Week 5-7: Model Generation
**Goal**: Convert problem data to mathematical models

**Tasks**:
1. Implement LP model generator
2. Implement transportation model
3. Implement assignment model
4. Add IP support
5. Test each generator
6. Add validation

**Deliverable**: Working generators for core problem types

### Week 8-9: Solver Integration
**Goal**: Solve models and get results

**Tasks**:
1. Test PuLP solver
2. Add OR-Tools (optional)
3. Handle different solution statuses
4. Extract results properly
5. Add sensitivity analysis

**Deliverable**: Successfully solve 20+ test problems

### Week 10-11: Results & UI
**Goal**: Make results understandable

**Tasks**:
1. Implement result interpreter
2. Add visualizations
3. Polish Streamlit UI
4. Add export features
5. Test end-to-end

**Deliverable**: Complete working prototype

### Week 12: Testing & Documentation
**Goal**: Final polish and demo

**Tasks**:
1. Write remaining tests
2. Fix bugs
3. Complete documentation
4. Prepare demo
5. Create presentation

**Deliverable**: Demo-ready system

## Daily Workflow

### Morning (30 min)
1. Review yesterday's work
2. Check if tests still pass
3. Plan today's tasks

### Coding Session (2-3 hours)
1. Pick ONE specific task
2. Write code
3. Test immediately
4. Commit to GitHub
5. Document what you did

### End of Day (15 min)
1. Run all tests
2. Commit final changes
3. Update progress tracker
4. Note any blockers

## Key Files to Understand

### 1. `src/agents/problem_classifier.py`
**What it does**: Uses Claude to understand problem descriptions

**Key functions**:
- `classify()`: Main entry point
- `_build_classification_prompt()`: Creates prompt for Claude

**How to use**:
```python
from src.agents.problem_classifier import ProblemClassifier

classifier = ProblemClassifier()
result = classifier.classify("Minimize shipping costs...")
print(result['problem_type'])
```

### 2. `src/modeling/model_generator.py`
**What it does**: Creates PuLP models from problem data

**Key functions**:
- `generate()`: Routes to appropriate generator
- `_generate_lp_model()`: Creates LP models
- `_generate_transportation_model()`: Creates transportation models

**How to use**:
```python
from src.modeling.model_generator import ModelGenerator

generator = ModelGenerator()
model = generator.generate(problem_data)
print(f"Variables: {len(model.variables())}")
```

### 3. `src/solvers/solver_interface.py`
**What it does**: Solves models and extracts results

**Key functions**:
- `solve()`: Main solving function
- `_extract_solution()`: Gets results from solved model

**How to use**:
```python
from src.solvers.solver_interface import SolverInterface

solver = SolverInterface("pulp")
solution = solver.solve(model)
print(f"Status: {solution['status']}")
print(f"Objective: {solution['objective_value']}")
```

### 4. `src/interpreters/result_interpreter.py`
**What it does**: Uses Claude to explain solutions

**Key functions**:
- `interpret()`: Generate explanation
- `generate_report()`: Create formatted report

**How to use**:
```python
from src.interpreters.result_interpreter import ResultInterpreter

interpreter = ResultInterpreter()
explanation = interpreter.interpret(solution, problem_data)
print(explanation['explanation'])
```

## Testing Strategy

### Unit Tests
Test individual functions:

```python
# tests/test_classifier.py
def test_problem_types_defined():
    classifier = ProblemClassifier()
    assert 'linear_programming' in classifier.PROBLEM_TYPES
```

### Integration Tests
Test complete workflows:

```python
@pytest.mark.integration
def test_end_to_end_lp():
    # Classify
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem_text)
    
    # Generate model
    generator = ModelGenerator()
    model = generator.generate(problem_data)
    
    # Solve
    solver = SolverInterface()
    solution = solver.solve(model)
    
    assert solution['status'] == 'Optimal'
```

### Run Tests
```bash
# All tests
pytest

# Specific file
pytest tests/test_classifier.py

# With coverage
pytest --cov=src tests/

# Skip integration tests (need API)
pytest -m "not integration"
```

## Common Development Tasks

### Add a New Problem Type

1. **Update classifier**:
   ```python
   # In src/agents/problem_classifier.py
   PROBLEM_TYPES = {
       ...
       "new_type": "Description of new type"
   }
   ```

2. **Add model generator**:
   ```python
   # In src/modeling/model_generator.py
   def _generate_new_type_model(self, problem_data):
       prob = pulp.LpProblem("NewType", sense)
       # Add variables, constraints, objective
       return prob
   ```

3. **Update routing**:
   ```python
   # In generate() method
   elif problem_type == 'new_type':
       return self._generate_new_type_model(problem_data)
   ```

4. **Test it**:
   ```python
   # tests/test_model_generator.py
   def test_new_type_generation():
       generator = ModelGenerator()
       model = generator.generate({"problem_type": "new_type"})
       assert model is not None
   ```

### Debug Claude API Issues

1. **Check API key**:
   ```python
   import os
   print(os.getenv('ANTHROPIC_API_KEY'))
   ```

2. **Test simple call**:
   ```python
   from anthropic import Anthropic
   client = Anthropic(api_key='your_key')
   response = client.messages.create(
       model="claude-sonnet-4-5-20250929",
       max_tokens=100,
       messages=[{"role": "user", "content": "Hi"}]
   )
   print(response.content[0].text)
   ```

3. **Check costs**:
   - Monitor usage at https://console.anthropic.com
   - Use caching for repeated prompts
   - Reduce max_tokens if needed

### Add Visualization

1. **Install library**: Already have matplotlib, plotly
2. **Create visualization function**:
   ```python
   # In src/utils/visualization.py
   import plotly.graph_objects as go
   
   def plot_solution(solution, problem_type):
       if problem_type == 'transportation':
           # Create network diagram
           fig = go.Figure(...)
           return fig
   ```

3. **Add to Streamlit**:
   ```python
   # In app.py
   import plotly.graph_objects as go
   st.plotly_chart(fig)
   ```

## Debugging Tips

### Problem: Classifier not working

**Check**:
1. API key is set correctly
2. Problem description has enough detail
3. Response is valid JSON

**Debug**:
```python
# Add print statements
print(f"Prompt: {prompt}")
print(f"Response: {response.content[0].text}")
```

### Problem: Model generation fails

**Check**:
1. Problem data has required fields
2. Data types are correct (lists, dicts, numbers)
3. Dimensions match (e.g., cost matrix size)

**Debug**:
```python
# Validate problem data
print(f"Problem type: {problem_data.get('problem_type')}")
print(f"Parameters: {problem_data.get('parameters')}")
```

### Problem: Solver returns infeasible

**Check**:
1. Constraints are not contradictory
2. Supply >= Demand (for transportation)
3. Bounds are reasonable

**Debug**:
```python
# Print model
print(prob)
for constraint in prob.constraints.values():
    print(constraint)
```

## Best Practices

### Code Style
- Use clear variable names
- Add docstrings to functions
- Comment complex logic
- Follow PEP 8

### Git Workflow
```bash
# Start new feature
git checkout -b feature/new-problem-type

# Make changes, test, commit
git add .
git commit -m "Add knapsack problem support"

# Push to GitHub
git push origin feature/new-problem-type
```

### Error Handling
```python
try:
    result = classifier.classify(problem)
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"API error: {e}")
```

## Resources

### Learning Resources
- PuLP: https://coin-or.github.io/pulp/
- OR-Tools: https://developers.google.com/optimization
- Anthropic: https://docs.anthropic.com
- Streamlit: https://docs.streamlit.io

### Getting Help
1. Check documentation
2. Review examples
3. Use Claude for debugging
4. Ask on OR forums
5. Open GitHub issue

## Milestones Checklist

### Week 2
- [ ] Environment set up
- [ ] Can call Claude API
- [ ] Streamlit runs
- [ ] Understand PuLP basics

### Week 4
- [ ] Classifier works
- [ ] Can identify 5+ problem types
- [ ] Tests pass

### Week 7
- [ ] LP generator works
- [ ] Transportation generator works
- [ ] Assignment generator works
- [ ] Models validate correctly

### Week 9
- [ ] Can solve LP problems
- [ ] Can solve IP problems
- [ ] Results extracted correctly
- [ ] 20+ test problems pass

### Week 11
- [ ] Result interpreter works
- [ ] UI is polished
- [ ] Visualizations work
- [ ] Export features work

### Week 12
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Demo prepared
- [ ] Code clean and commented

## Final Project Checklist

Before submission:
- [ ] All tests pass
- [ ] Code is documented
- [ ] README is complete
- [ ] Examples work
- [ ] Demo prepared
- [ ] GitHub repo clean
- [ ] Requirements.txt updated
- [ ] .env.example has all variables

Good luck! Remember: progress over perfection. Build incrementally, test often, and ask for help early.
