"""
Problem Classifier - Uses AI to identify problem type and extract parameters
Supports both Anthropic Claude and OpenAI models.
"""

import os
from typing import Dict, Any, Optional
import json
from src.utils.api_client import APIClient


class ProblemClassifier:
    """
    Classifies optimization problems and extracts relevant parameters
    using AI (Anthropic Claude or OpenAI).
    """
    
    PROBLEM_TYPES = {
        "linear_programming": "Linear optimization with continuous variables",
        "integer_programming": "Optimization with integer decision variables",
        "mixed_integer_programming": "Mix of continuous and integer variables",
        "transportation": "Moving goods from sources to destinations",
        "assignment": "Matching resources to tasks optimally",
        "scheduling": "Sequencing tasks over time",
        "knapsack": "Selecting items with capacity constraints",
        "network_flow": "Flow optimization through networks",
        "routing": "Vehicle routing and path optimization",
        "cutting_stock": "Minimizing waste when cutting materials"
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the classifier with AI API.
        
        Args:
            api_key: API key (optional, reads from environment if not provided)
            provider: 'anthropic' or 'openai' (optional, auto-detects if not provided)
            model: Model name (optional, uses default if not provided)
        """
        self.api_client = APIClient(provider=provider, api_key=api_key, model=model)
        self.model = self.api_client.get_model_name()
    
    def classify(self, problem_description: str) -> Dict[str, Any]:
        """
        Classify a problem description and extract structured parameters.
        
        Args:
            problem_description: Natural language description of the problem
            
        Returns:
            Dictionary with problem_type and extracted parameters
        """
        
        prompt = self._build_classification_prompt(problem_description)
        
        try:
            response = self.api_client.create_message(
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=4096,
                temperature=0.3
            )
            
            # Extract JSON from response
            result_text = response['content']
            
            # Parse JSON (Claude should return valid JSON)
            result = json.loads(result_text)
            
            # Validate result
            if "problem_type" not in result:
                raise ValueError("Response missing 'problem_type' field")
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Classification failed: {str(e)}")
    
    def _build_classification_prompt(self, description: str) -> str:
        """Build the prompt for AI to classify the problem."""
        
        problem_types_list = "\n".join([
            f"- {key}: {value}" 
            for key, value in self.PROBLEM_TYPES.items()
        ])
        
        prompt = f"""You are an expert in Operations Research. Analyze the following problem description and:

1. Identify the problem type from these categories:
{problem_types_list}

2. Extract all relevant parameters including:
   - Decision variables (what needs to be decided)
   - Objective function (what to minimize/maximize)
   - Constraints (limitations and requirements)
   - Data values (numbers, capacities, costs, etc.)

3. Return ONLY a valid JSON object with this structure:
{{
    "problem_type": "one_of_the_types_above",
    "objective": "minimize" or "maximize",
    "objective_description": "brief description",
    "decision_variables": ["list of variable descriptions"],
    "constraints": ["list of constraint descriptions"],
    "parameters": {{
        "key": "value pairs of extracted numerical data"
    }},
    "confidence": 0.0 to 1.0,
    "notes": "any clarifications or assumptions"
}}

Problem Description:
{description}

Return ONLY the JSON object, no additional text.
"""
        return prompt
    
    def get_problem_template(self, problem_type: str) -> Dict[str, Any]:
        """
        Get a template structure for a specific problem type.
        
        Args:
            problem_type: Type of problem
            
        Returns:
            Template dictionary
        """
        
        templates = {
            "linear_programming": {
                "variables": [],
                "objective_coefficients": [],
                "constraint_coefficients": [],
                "constraint_bounds": [],
                "variable_bounds": []
            },
            "transportation": {
                "sources": [],
                "destinations": [],
                "supply": [],
                "demand": [],
                "costs": []
            },
            "assignment": {
                "agents": [],
                "tasks": [],
                "costs": []
            }
            # Add more templates as needed
        }
        
        return templates.get(problem_type, {})


if __name__ == "__main__":
    # Example usage
    classifier = ProblemClassifier()
    
    test_problem = """
    I need to minimize transportation costs between 3 warehouses and 4 stores.
    Warehouse supplies: [100, 150, 200]
    Store demands: [80, 120, 90, 110]
    Cost per unit from each warehouse to each store (3x4 matrix):
    [[5, 8, 6, 7],
     [6, 7, 9, 5],
     [8, 6, 7, 9]]
    """
    
    result = classifier.classify(test_problem)
    print(json.dumps(result, indent=2))
