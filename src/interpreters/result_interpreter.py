"""
Result Interpreter - Uses Claude AI to explain solutions in plain language
"""

import os
from typing import Dict, Any, Optional
import json
from anthropic import Anthropic


class ResultInterpreter:
    """
    Interprets optimization results and generates human-readable explanations
    using Claude AI.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the interpreter with Anthropic API."""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = os.getenv('DEFAULT_MODEL', 'claude-sonnet-4-5-20250929')
    
    def interpret(
        self, 
        solution: Dict[str, Any], 
        problem_data: Dict[str, Any],
        detail_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a plain-language explanation of the solution.
        
        Args:
            solution: Solution dictionary from SolverInterface
            problem_data: Original problem data from classifier
            detail_level: 'brief', 'medium', or 'detailed'
            
        Returns:
            Dictionary with various explanation formats
        """
        
        # Check if solution is optimal
        if solution["status"] != "Optimal":
            return self._explain_non_optimal(solution, problem_data)
        
        prompt = self._build_interpretation_prompt(solution, problem_data, detail_level)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.5,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            explanation = response.content[0].text
            
            return {
                "status": "success",
                "explanation": explanation,
                "solution_summary": self._create_summary(solution),
                "key_insights": self._extract_key_insights(solution),
                "recommendations": []  # Could be enhanced
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "explanation": "Failed to generate explanation"
            }
    
    def _build_interpretation_prompt(
        self, 
        solution: Dict[str, Any], 
        problem_data: Dict[str, Any],
        detail_level: str
    ) -> str:
        """Build prompt for Claude to interpret results."""
        
        detail_instructions = {
            "brief": "Provide a 2-3 sentence summary of the key results and what action should be taken.",
            "medium": "Provide a clear explanation of the results, key decisions, and their business impact in 1-2 paragraphs.",
            "detailed": "Provide a comprehensive analysis including the solution, implications, trade-offs, and recommendations."
        }
        
        prompt = f"""You are an Operations Research consultant explaining optimization results to a business stakeholder.

PROBLEM CONTEXT:
- Type: {problem_data.get('problem_type', 'Unknown')}
- Objective: {problem_data.get('objective', 'Unknown')} {problem_data.get('objective_description', '')}
- Decision Variables: {problem_data.get('decision_variables', [])}
- Constraints: {problem_data.get('constraints', [])}

SOLUTION:
- Status: {solution['status']}
- Objective Value: {solution.get('objective_value', 'N/A')}
- Solve Time: {solution.get('solve_time', 'N/A')} seconds
- Number of Variables: {solution['model_info']['num_variables']}
- Number of Constraints: {solution['model_info']['num_constraints']}

KEY RESULTS:
{json.dumps(solution.get('variables', {}), indent=2)}

TASK:
{detail_instructions.get(detail_level, detail_instructions['medium'])}

Focus on:
1. What decisions should be made (the variable values)
2. What the business impact is (the objective value)
3. Any important patterns or insights
4. Any constraints that are binding (tight)

Write in clear, business-friendly language. Avoid mathematical jargon where possible.
"""
        return prompt
    
    def _explain_non_optimal(
        self, 
        solution: Dict[str, Any], 
        problem_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Explain why a solution is not optimal."""
        
        status = solution["status"]
        
        explanations = {
            "Infeasible": """
The problem is infeasible, meaning there is no solution that satisfies all constraints.
This typically happens when:
- Constraints are contradictory
- Demands exceed available supply
- Requirements are impossible to meet simultaneously

Recommendations:
- Review and relax some constraints
- Check if data is correct
- Consider if the problem formulation needs adjustment
            """,
            "Unbounded": """
The problem is unbounded, meaning the objective can be improved infinitely.
This usually indicates:
- Missing constraints on variables
- Incorrect problem formulation
- Some variables have no upper bounds when they should

Recommendations:
- Add appropriate bounds to decision variables
- Review the problem formulation
- Check if constraints are missing
            """,
            "Time Limit Reached": """
The solver reached the time limit before finding an optimal solution.
The current best solution may be:
- Near-optimal (check the gap)
- Usable for practical purposes

Recommendations:
- Increase the time limit
- Use a commercial solver for better performance
- Simplify the problem if possible
            """
        }
        
        return {
            "status": "non_optimal",
            "explanation": explanations.get(status, f"Solution status: {status}"),
            "solver_status": status,
            "recommendations": []
        }
    
    def _create_summary(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Create a concise summary of the solution."""
        
        # Count variables at bounds
        at_bounds = 0
        for var_info in solution.get('variables', {}).values():
            value = var_info.get('value', 0)
            lower = var_info.get('lower_bound')
            upper = var_info.get('upper_bound')
            
            if lower is not None and abs(value - lower) < 1e-6:
                at_bounds += 1
            elif upper is not None and abs(value - upper) < 1e-6:
                at_bounds += 1
        
        # Count binding constraints
        binding = 0
        for const_info in solution.get('constraints', {}).values():
            slack = const_info.get('slack', 1)
            if slack is not None and abs(slack) < 1e-6:
                binding += 1
        
        return {
            "objective_value": solution.get('objective_value'),
            "status": solution.get('status'),
            "solve_time": solution.get('solve_time'),
            "total_variables": len(solution.get('variables', {})),
            "total_constraints": len(solution.get('constraints', {})),
            "variables_at_bounds": at_bounds,
            "binding_constraints": binding
        }
    
    def _extract_key_insights(self, solution: Dict[str, Any]) -> list:
        """Extract key insights from the solution."""
        
        insights = []
        
        summary = self._create_summary(solution)
        
        # Insight about binding constraints
        if summary['binding_constraints'] > 0:
            insights.append(
                f"{summary['binding_constraints']} constraint(s) are binding, "
                "indicating these are the critical limitations."
            )
        
        # Insight about variables at bounds
        if summary['variables_at_bounds'] > 0:
            insights.append(
                f"{summary['variables_at_bounds']} variable(s) are at their limits, "
                "suggesting potential for improvement if bounds are relaxed."
            )
        
        return insights
    
    def generate_report(
        self,
        solution: Dict[str, Any],
        problem_data: Dict[str, Any],
        format: str = "markdown"
    ) -> str:
        """
        Generate a formatted report.
        
        Args:
            solution: Solution data
            problem_data: Problem data
            format: 'markdown', 'html', or 'text'
            
        Returns:
            Formatted report string
        """
        
        interpretation = self.interpret(solution, problem_data, detail_level="detailed")
        summary = self._create_summary(solution)
        
        if format == "markdown":
            return self._generate_markdown_report(interpretation, summary, solution, problem_data)
        elif format == "html":
            return self._generate_html_report(interpretation, summary, solution, problem_data)
        else:
            return self._generate_text_report(interpretation, summary, solution, problem_data)
    
    def _generate_markdown_report(
        self,
        interpretation: Dict[str, Any],
        summary: Dict[str, Any],
        solution: Dict[str, Any],
        problem_data: Dict[str, Any]
    ) -> str:
        """Generate a Markdown-formatted report."""
        
        report = f"""# Optimization Results Report

## Problem Summary
- **Type**: {problem_data.get('problem_type', 'Unknown')}
- **Objective**: {problem_data.get('objective', '')} {problem_data.get('objective_description', '')}

## Solution Summary
- **Status**: {summary['status']}
- **Objective Value**: {summary['objective_value']}
- **Solve Time**: {summary['solve_time']}s
- **Variables**: {summary['total_variables']}
- **Constraints**: {summary['total_constraints']}

## Interpretation
{interpretation.get('explanation', 'No explanation available')}

## Key Insights
"""
        for insight in interpretation.get('key_insights', []):
            report += f"- {insight}\n"
        
        report += "\n## Decision Variables\n"
        for var_name, var_info in solution.get('variables', {}).items():
            report += f"- **{var_name}**: {var_info.get('value', 0)}\n"
        
        return report
    
    def _generate_html_report(self, *args) -> str:
        """Generate HTML-formatted report."""
        # TODO: Implement HTML generation
        return "<html><body><h1>Report</h1></body></html>"
    
    def _generate_text_report(self, *args) -> str:
        """Generate plain text report."""
        # TODO: Implement text generation
        return "Text report"


if __name__ == "__main__":
    # Example usage
    interpreter = ResultInterpreter()
    
    test_solution = {
        "status": "Optimal",
        "objective_value": 1250.0,
        "solve_time": 2.3,
        "model_info": {
            "num_variables": 12,
            "num_constraints": 7,
            "sense": "minimize"
        },
        "variables": {
            "x_0_0": {"value": 50, "lower_bound": 0, "upper_bound": None},
            "x_0_1": {"value": 50, "lower_bound": 0, "upper_bound": None},
            "x_1_0": {"value": 30, "lower_bound": 0, "upper_bound": None}
        },
        "constraints": {}
    }
    
    test_problem = {
        "problem_type": "transportation",
        "objective": "minimize",
        "objective_description": "total transportation cost"
    }
    
    result = interpreter.interpret(test_solution, test_problem)
    print(result['explanation'])
