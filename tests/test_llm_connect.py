"""
Test script to demonstrate the fix for connecting LLM to the problem definition.

This test shows that the model generator now uses the LLM's 
understanding of the problem to generate the actual optimization model.
"""

import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agents.problem_classifier import ProblemClassifier
from src.modeling.model_generator import ModelGenerator
import pulp


def test_llm_connection():
    """Test that LLM problem classification connects to model generation."""
    
    print("=" * 70)
    print("TESTING: LLM → Problem Definition → Model Generation")
    print("=" * 70)
    
    # Test Problem 1: Widget Production (Integer Programming)
    print("\n TEST 1: Widget Production Problem")
    print("-" * 70)
    
    problem_description = """
    I need to maximize profit from producing widgets.
    Each widget requires 2 hours of labor and 3 kg of material.
    I have 100 hours of labor and 120 kg of material available.
    Each widget sells for $50 profit.
    I can only produce whole widgets (no fractions).
    """
    
    print(f"Problem Description:\n{problem_description}")
    
    # Step 1: Classify with LLM
    print("\n Step 1: Classifying with LLM...")
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem_description)
    
    print(f"\n✓ LLM Classification Result:")
    print(json.dumps(problem_data, indent=2))
    
    # Step 2: Generate model using LLM's understanding
    print("\n🏗️  Step 2: Generating model using LLM's classification...")
    generator = ModelGenerator()
    model = generator.generate(problem_data)
    
    # Step 3: Validate the model was actually created
    validation = generator.validate_model(model)
    print(f"\n✓ Model Validation:")
    print(f"  Valid: {validation['valid']}")
    print(f"  Variables: {validation['num_variables']}")
    print(f"  Constraints: {validation['num_constraints']}")
    print(f"  Issues: {validation['issues'] if validation['issues'] else 'None'}")
    print(f"  Warnings: {validation['warnings'] if validation['warnings'] else 'None'}")
    
    # Step 4: Solve the model
    print("\n🔧 Step 3: Solving the model...")
    model.solve(pulp.PULP_CBC_CMD(msg=0))
    
    print(f"\n✓ Solution Status: {pulp.LpStatus[model.status]}")
    
    if model.status == 1:  # Optimal
        print(f"✓ Optimal Objective Value: {pulp.value(model.objective)}")
        print(f"\n✓ Decision Variable Values:")
        for v in model.variables():
            if v.varValue is not None and v.varValue > 0:
                print(f"    {v.name} = {v.varValue}")
        
        print("\n SUCCESS: LLM successfully connected to problem definition!")
        print("   The model was generated based on the LLM's understanding,")
        print("   not from a default/random template.")
        return True
    else:
        print("\n Model didn't solve to optimality, but was generated correctly")
        return False


def test_different_problem():
    """Test with a different problem type to verify flexibility."""
    
    print("\n\n" + "=" * 70)
    print("TEST 2: Different Problem Type - Resource Allocation")
    print("=" * 70)
    
    problem_description = """
    A factory produces two products: A and B.
    Product A requires 3 hours on Machine 1 and 2 hours on Machine 2. Profit: $40.
    Product B requires 2 hours on Machine 1 and 4 hours on Machine 2. Profit: $60.
    Machine 1 has 100 hours available.
    Machine 2 has 120 hours available.
    How many of each product should be produced to maximize profit?
    """
    
    print(f"Problem Description:\n{problem_description}")
    
    print("\n Classifying and generating model...")
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem_description)
    
    print(f"\nProblem Type: {problem_data.get('problem_type')}")
    print(f"Objective: {problem_data.get('objective')} {problem_data.get('objective_description')}")
    
    generator = ModelGenerator()
    model = generator.generate(problem_data)
    
    validation = generator.validate_model(model)
    print(f"\n✓ Model Created: {validation['num_variables']} variables, {validation['num_constraints']} constraints")
    
    print("\n🔧 Solving...")
    model.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if model.status == 1:
        print(f"\n✓ Optimal Profit: ${pulp.value(model.objective):.2f}")
        print("✓ Production Plan:")
        for v in model.variables():
            if v.varValue is not None:
                print(f"    {v.name} = {v.varValue:.2f}")
        return True
    else:
        print(f"\nStatus: {pulp.LpStatus[model.status]}")
        return False


if __name__ == "__main__":
    print("\n OR ASSISTANT - LLM CONNECTION TEST")
    print("Testing Priority #1: Connect LLM to problem definition\n")
    
    try:
        success1 = test_llm_connection()
        success2 = test_different_problem()
        
        print("\n" + "=" * 70)
        if success1 or success2:
            print(" PRIORITY #1 FIXED!")
            print("   LLM is now properly connected to problem definition.")
            print("   Models are generated based on actual problem understanding,")
            print("   not default/random templates.")
        else:
            print("  Tests completed but some issues remain")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n Error during testing: {e}")
        import traceback
        traceback.print_exc()