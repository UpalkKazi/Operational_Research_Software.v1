"""
Model Generator - Creates mathematical models from problem data
Supports both Anthropic Claude and OpenAI models.
"""

from typing import Dict, Any, Optional
import pulp
import os
import json
from src.utils.api_client import APIClient


class ModelGenerator:
    """
    Generates mathematical optimization models from structured problem data.
    Can use AI (Anthropic Claude or OpenAI) to help generate model code dynamically.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the model generator.
        
        Args:
            api_key: API key (optional, reads from environment if not provided)
            provider: 'anthropic' or 'openai' (optional, auto-detects if not provided)
            model: Model name (optional, uses default if not provided)
        """
        try:
            self.api_client = APIClient(provider=provider, api_key=api_key, model=model)
            self.model = self.api_client.get_model_name()
        except ValueError:
            # API not configured - model generation without AI will still work
            self.api_client = None
            self.model = None
    
    def generate(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """
        Generate a PuLP model from problem data.
        
        Args:
            problem_data: Structured problem information from classifier
            
        Returns:
            PuLP LpProblem object
        """
        
        problem_type = problem_data.get('problem_type', '')
        
        # Route to appropriate generator
        if problem_type == 'transportation':
            return self._generate_transportation_model(problem_data)
        elif problem_type == 'assignment':
            return self._generate_assignment_model(problem_data)
        else:
            # For all other types like Integer and Linear Programming, use AI based generation
            # Ensures the LLM's understanding is actually used
            return self._generate_with_ai(problem_data)
    
    def _generate_transportation_model(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Generate a transportation problem model."""
        
        params = problem_data.get('parameters', {})
        
        # Extract data
        sources = params.get('sources', [])
        destinations = params.get('destinations', [])
        supply = params.get('supply', [])
        demand = params.get('demand', [])
        costs = params.get('costs', [])
        
        # Create problem
        prob = pulp.LpProblem("Transportation_Problem", pulp.LpMinimize)
        
        # Create variables: x[i][j] = amount shipped from source i to destination j
        num_sources = len(sources) if sources else len(supply)
        num_destinations = len(destinations) if destinations else len(demand)
        
        x = pulp.LpVariable.dicts(
            "ship",
            ((i, j) for i in range(num_sources) for j in range(num_destinations)),
            lowBound=0,
            cat='Continuous'
        )
        
        # Objective: Minimize total cost
        if costs:
            prob += pulp.lpSum([
                costs[i][j] * x[i, j]
                for i in range(num_sources)
                for j in range(num_destinations)
            ]), "Total_Cost"
        
        # Supply constraints
        if supply:
            for i in range(num_sources):
                prob += (
                    pulp.lpSum([x[i, j] for j in range(num_destinations)]) <= supply[i],
                    f"Supply_{i}"
                )
        
        # Demand constraints
        if demand:
            for j in range(num_destinations):
                prob += (
                    pulp.lpSum([x[i, j] for i in range(num_sources)]) >= demand[j],
                    f"Demand_{j}"
                )
        
        return prob
    
    def _generate_assignment_model(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Generate an assignment problem model."""
        
        params = problem_data.get('parameters', {})
        costs = params.get('costs', [])
        
        n = len(costs) if costs else 0
        
        prob = pulp.LpProblem("Assignment_Problem", pulp.LpMinimize)
        
        # Binary variables: x[i][j] = 1 if agent i assigned to task j
        x = pulp.LpVariable.dicts(
            "assign",
            ((i, j) for i in range(n) for j in range(n)),
            cat='Binary'
        )
        
        # Objective
        if costs:
            prob += pulp.lpSum([
                costs[i][j] * x[i, j]
                for i in range(n)
                for j in range(n)
            ]), "Total_Cost"
        
        # Each agent assigned to exactly one task
        for i in range(n):
            prob += pulp.lpSum([x[i, j] for j in range(n)]) == 1, f"Agent_{i}"
        
        # Each task assigned to exactly one agent
        for j in range(n):
            prob += pulp.lpSum([x[i, j] for i in range(n)]) == 1, f"Task_{j}"
        
        return prob
    
    def _generate_with_ai(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Use AI to generate model code based on the classified problem type."""
        
        if not self.api_client:
            raise ValueError("AI API not configured for dynamic model generation")
        
        prompt = f"""You are an expert in Operations Research using Python and PuLP.

Generate Python code to create a PuLP model for this problem:

Problem Type: {problem_data.get('problem_type')}
Objective: {problem_data.get('objective')} {problem_data.get('objective_description')}
Variables: {problem_data.get('decision_variables')}
Constraints: {problem_data.get('constraints')}
Parameters: {json.dumps(problem_data.get('parameters', {}), indent=2)}

Requirements:
1. Import pulp
2. Create a function called 'create_model()' that returns a pulp.LpProblem
3. Use clear variable names
4. Add comments explaining each constraint
5. Return only the complete, executable Python code

Return ONLY the Python code, no explanations.

Example structure:
```python
import pulp

def create_model():
    # Create problem
    prob = pulp.LpProblem("Problem_Name", pulp.LpMinimize)  # or LpMaximize
    
    # Define variables
    # ... your variables here ...
    
    # Set objective
    prob += objective_expression, "Objective"
    
    # Add constraints
    # ... your constraints here ...
    
    return prob

"""
        
        try:
            response = self.api_client.create_message(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3
            )
            
            code = response['content']

            # Clean up the code (remove markdown if present)
            if '```python' in code:
                code = code.split('```python')[1].split('```')[0]
            elif '```' in code:
                code = code.split('```')[1].split('```')[0]
            
            code = code.strip()
            
            # Execute the generated code
            local_vars = {}
            exec(code, {"pulp": pulp}, local_vars)
            
            if 'create_model' in local_vars:
                model = local_vars['create_model']()
            
            # Validate that the model was actually created with content
                validation = self.validate_model(model)
                if not validation['valid']:
                    raise ValueError(f"Generated model is invalid: {validation['issues']}")
                    
                return model
            else:
                raise ValueError("Generated code doesn't contain create_model function")
                
        except Exception as e:
            raise RuntimeError(f"Model generation with AI failed: {str(e)}\n\nGenerated code:\n{code if 'code' in locals() else 'No code generated'}")
    
    def validate_model(self, model: pulp.LpProblem) -> Dict[str, Any]:
        """
        Validate a model for common issues.
        
        Returns:
            Dictionary with validation results
        """
        
        issues = []
        warnings = []
        
        # Check for variables
        if not model.variables():
            issues.append("No decision variables defined")
        
        # Check for objective
        if model.objective is None:
            issues.append("No objective function defined")
        
        # Check for constraints
        if not model.constraints:
            warnings.append("No constraints defined - problem may be unbounded")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "num_variables": len(model.variables()),
            "num_constraints": len(model.constraints)
        }


if __name__ == "__main__":
    # Example usage
    generator = ModelGenerator()
    
    # Test with a simple problem
    test_data = {
        "problem_type": "integer_programming",
        "objective": "maximize",
        "objective_description": "profit from producing widgets",
        "decision_variables": ["number of widgets to produce"],
        "constraints": [
            "Cannot exceed 100 hours of labor",
            "Cannot exceed 120 kg of material"
        ],
        "parameters": {
            "profit_per_widget": 50,
            "labor_hours_per_widget": 2,
            "material_kg_per_widget": 3,
            "available_labor_hours": 100,
            "available_material_kg": 120
        },
        "confidence": 0.95,
        "notes": "Widget production must be integer values"
    }
    
    print("Generating model from problem data...")
    model = generator.generate(test_data)
    
    validation = generator.validate_model(model)
    print("\nModel validation:", validation)
    
    if validation['valid']:
        print(f"\n✓ Model successfully created!")
        print(f"  Variables: {validation['num_variables']}")
        print(f"  Constraints: {validation['num_constraints']}")
        
        # Try to solve it
        print("\nAttempting to solve...")
        model.solve()
        print(f"Status: {pulp.LpStatus[model.status]}")
        
        if model.status == 1:  # Optimal
            print(f"Objective value: {pulp.value(model.objective)}")
            print("\nVariable values:")
            for v in model.variables():
                print(f"  {v.name} = {v.varValue}")
