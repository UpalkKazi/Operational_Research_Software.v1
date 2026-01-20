"""
Solver Interface - Unified interface for different OR solvers
"""

from typing import Dict, Any, Optional
import pulp
import time
from enum import Enum


class SolverStatus(Enum):
    """Solver status codes"""
    OPTIMAL = "Optimal"
    INFEASIBLE = "Infeasible"
    UNBOUNDED = "Unbounded"
    NOT_SOLVED = "Not Solved"
    TIME_LIMIT = "Time Limit Reached"
    ERROR = "Error"


class SolverInterface:
    """
    Unified interface for various optimization solvers.
    Currently supports PuLP, with extensibility for OR-Tools, CVXPY, etc.
    """
    
    def __init__(self, solver_type: str = "pulp"):
        """
        Initialize solver interface.
        
        Args:
            solver_type: Type of solver ('pulp', 'ortools', 'cvxpy', 'gurobi', 'cplex')
        """
        self.solver_type = solver_type.lower()
        self.solver = self._initialize_solver()
    
    def _initialize_solver(self):
        """Initialize the appropriate solver."""
        
        if self.solver_type == "pulp":
            # Use default PuLP solver (CBC)
            return pulp.PULP_CBC_CMD(msg=1)
        
        elif self.solver_type == "gurobi":
            try:
                return pulp.GUROBI_CMD(msg=1)
            except:
                raise RuntimeError("Gurobi not available. Install and configure license.")
        
        elif self.solver_type == "cplex":
            try:
                return pulp.CPLEX_CMD(msg=1)
            except:
                raise RuntimeError("CPLEX not available. Install and configure license.")
        
        elif self.solver_type == "glpk":
            try:
                return pulp.GLPK_CMD(msg=1)
            except:
                raise RuntimeError("GLPK not available.")
        
        else:
            # Default to CBC
            return pulp.PULP_CBC_CMD(msg=1)
    
    def solve(
        self, 
        model: pulp.LpProblem, 
        max_time: Optional[int] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Solve the optimization model.
        
        Args:
            model: PuLP LpProblem object
            max_time: Maximum solution time in seconds
            verbose: Print solver output
            
        Returns:
            Dictionary containing solution information
        """
        
        start_time = time.time()
        
        try:
            # Set time limit if specified
            if max_time and hasattr(self.solver, 'timeLimit'):
                self.solver.timeLimit = max_time
            
            # Solve
            status = model.solve(self.solver)
            
            solve_time = time.time() - start_time
            
            # Extract solution
            solution = self._extract_solution(model, status, solve_time)
            
            return solution
            
        except Exception as e:
            return {
                "status": SolverStatus.ERROR.value,
                "error": str(e),
                "solve_time": time.time() - start_time
            }
    
    def _extract_solution(
        self, 
        model: pulp.LpProblem, 
        status: int,
        solve_time: float
    ) -> Dict[str, Any]:
        """Extract solution information from solved model."""
        
        # Map PuLP status to our status enum
        status_map = {
            pulp.LpStatusOptimal: SolverStatus.OPTIMAL,
            pulp.LpStatusInfeasible: SolverStatus.INFEASIBLE,
            pulp.LpStatusUnbounded: SolverStatus.UNBOUNDED,
            pulp.LpStatusNotSolved: SolverStatus.NOT_SOLVED
        }
        
        solver_status = status_map.get(status, SolverStatus.ERROR)
        
        solution = {
            "status": solver_status.value,
            "status_code": status,
            "solve_time": round(solve_time, 3),
            "solver": self.solver_type,
            "objective_value": None,
            "variables": {},
            "constraints": {},
            "model_info": {
                "name": model.name,
                "num_variables": len(model.variables()),
                "num_constraints": len(model.constraints),
                "sense": "minimize" if model.sense == pulp.LpMinimize else "maximize"
            }
        }
        
        # If optimal, extract values
        if solver_status == SolverStatus.OPTIMAL:
            # Objective value
            solution["objective_value"] = pulp.value(model.objective)
            
            # Variable values
            for var in model.variables():
                solution["variables"][var.name] = {
                    "value": var.varValue,
                    "lower_bound": var.lowBound,
                    "upper_bound": var.upBound,
                    "category": var.cat
                }
            
            # Constraint information (slack, shadow prices)
            for name, constraint in model.constraints.items():
                solution["constraints"][name] = {
                    "slack": constraint.slack if hasattr(constraint, 'slack') else None,
                    "shadow_price": constraint.pi if hasattr(constraint, 'pi') else None
                }
        
        return solution
    
    def get_solver_info(self) -> Dict[str, Any]:
        """Get information about the current solver."""
        
        return {
            "solver_type": self.solver_type,
            "solver_object": str(self.solver),
            "available": True  # Could check actual availability
        }
    
    @staticmethod
    def list_available_solvers() -> Dict[str, bool]:
        """List all solvers and their availability."""
        
        solvers = {
            "pulp_cbc": True,  # Always available with PuLP
            "gurobi": False,
            "cplex": False,
            "glpk": False,
            "ortools": False,
            "cvxpy": False
        }
        
        # Check Gurobi
        try:
            pulp.GUROBI_CMD(msg=0).available()
            solvers["gurobi"] = True
        except:
            pass
        
        # Check CPLEX
        try:
            pulp.CPLEX_CMD(msg=0).available()
            solvers["cplex"] = True
        except:
            pass
        
        # Check GLPK
        try:
            pulp.GLPK_CMD(msg=0).available()
            solvers["glpk"] = True
        except:
            pass
        
        return solvers


class SensitivityAnalyzer:
    """Perform sensitivity analysis on solutions."""
    
    def __init__(self, solution: Dict[str, Any]):
        """Initialize with a solution."""
        self.solution = solution
    
    def analyze_shadow_prices(self) -> Dict[str, Any]:
        """Analyze shadow prices (dual values) of constraints."""
        
        if self.solution["status"] != SolverStatus.OPTIMAL.value:
            return {"error": "Solution not optimal"}
        
        shadow_prices = {}
        for name, info in self.solution["constraints"].items():
            if info.get("shadow_price") is not None:
                shadow_prices[name] = {
                    "shadow_price": info["shadow_price"],
                    "slack": info.get("slack", 0),
                    "binding": abs(info.get("slack", 1)) < 1e-6
                }
        
        return shadow_prices
    
    def analyze_variable_slack(self) -> Dict[str, Any]:
        """Analyze variable slack (distance from bounds)."""
        
        if self.solution["status"] != SolverStatus.OPTIMAL.value:
            return {"error": "Solution not optimal"}
        
        slack_analysis = {}
        for name, info in self.solution["variables"].items():
            value = info["value"]
            lower = info.get("lower_bound")
            upper = info.get("upper_bound")
            
            slack_analysis[name] = {
                "value": value,
                "lower_slack": value - lower if lower is not None else None,
                "upper_slack": upper - value if upper is not None else None,
                "at_bound": False
            }
            
            # Check if at bound
            if lower is not None and abs(value - lower) < 1e-6:
                slack_analysis[name]["at_bound"] = True
            if upper is not None and abs(value - upper) < 1e-6:
                slack_analysis[name]["at_bound"] = True
        
        return slack_analysis


if __name__ == "__main__":
    # Example usage
    print("Available solvers:", SolverInterface.list_available_solvers())
    
    # Create a simple LP problem
    prob = pulp.LpProblem("Test", pulp.LpMinimize)
    x = pulp.LpVariable("x", lowBound=0)
    y = pulp.LpVariable("y", lowBound=0)
    
    prob += 2*x + 3*y, "Cost"
    prob += x + y >= 10, "Constraint1"
    prob += 2*x + y >= 15, "Constraint2"
    
    # Solve
    solver = SolverInterface("pulp")
    solution = solver.solve(prob)
    
    print("\nSolution:")
    print(f"Status: {solution['status']}")
    print(f"Objective: {solution['objective_value']}")
    print(f"Solve time: {solution['solve_time']}s")
    print("\nVariables:")
    for var, info in solution['variables'].items():
        print(f"  {var} = {info['value']}")
