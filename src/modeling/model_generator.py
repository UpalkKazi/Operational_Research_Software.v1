"""
Model Generator - Creates mathematical models from problem data
"""

from typing import Dict, Any, Optional
import pulp
from anthropic import Anthropic
import os
import json


class ModelGenerator:
    """
    Generates mathematical optimization models from structured problem data.
    Can use Claude AI to help generate model code dynamically.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the model generator."""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.model = os.getenv('DEFAULT_MODEL', 'claude-sonnet-4-5-20250929')
    
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
        if problem_type == 'linear_programming':
            return self._generate_lp_model(problem_data)
        elif problem_type == 'transportation':
            return self._generate_transportation_model(problem_data)
        elif problem_type == 'assignment':
            return self._generate_assignment_model(problem_data)
        elif problem_type in ['integer_programming', 'mixed_integer_programming']:
            return self._generate_ip_model(problem_data)
        else:
            # Use Claude to generate model code dynamically
            return self._generate_with_claude(problem_data)
    
    def _generate_lp_model(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Generate a basic linear programming model."""
        
        # Determine sense (minimize or maximize)
        sense = pulp.LpMinimize if problem_data.get('objective') == 'minimize' else pulp.LpMaximize
        
        # Create problem
        prob = pulp.LpProblem("LP_Problem", sense)
        
        # TODO: Extract variables and constraints from problem_data
        # This is a placeholder - actual implementation depends on data structure
        
        return prob
    
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
    
    def _generate_ip_model(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Generate an integer programming model."""
        
        # Similar to LP but with integer variables
        sense = pulp.LpMinimize if problem_data.get('objective') == 'minimize' else pulp.LpMaximize
        prob = pulp.LpProblem("IP_Problem", sense)
        
        # TODO: Implement based on problem_data structure
        
        return prob
    
    def _generate_with_claude(self, problem_data: Dict[str, Any]) -> pulp.LpProblem:
        """Use Claude to generate model code for complex problems."""
        
        if not self.client:
            raise ValueError("Claude API not configured for dynamic model generation")
        
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
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            code = response.content[0].text
            
            # Execute the generated code
            local_vars = {}
            exec(code, {"pulp": pulp}, local_vars)
            
            if 'create_model' in local_vars:
                return local_vars['create_model']()
            else:
                raise ValueError("Generated code doesn't contain create_model function")
                
        except Exception as e:
            raise RuntimeError(f"Model generation with Claude failed: {str(e)}")
    
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
    
    test_data = {
        "problem_type": "transportation",
        "objective": "minimize",
        "parameters": {
            "supply": [100, 150, 200],
            "demand": [80, 120, 90, 110],
            "costs": [
                [5, 8, 6, 7],
                [6, 7, 9, 5],
                [8, 6, 7, 9]
            ]
        }
    }
    
    model = generator.generate(test_data)
    validation = generator.validate_model(model)
    
    print("Model validation:", validation)
    print("\nModel variables:", len(model.variables()))
    print("Model constraints:", len(model.constraints))
