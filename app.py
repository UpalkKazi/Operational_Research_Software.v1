"""
OR Assistant - Main Streamlit Application
AI-Powered Operations Research Tool
"""

import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import project modules (these will be implemented)
try:
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    from src.solvers.solver_interface import SolverInterface
    from src.interpreters.result_interpreter import ResultInterpreter
except ImportError:
    st.warning("⚠️ Some modules are not yet implemented. See development guide.")

# Page configuration
st.set_page_config(
    page_title="OR Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown('<p class="main-header">🎯 OR Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Operations Research Solutions</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Solver selection
    solver_type = st.selectbox(
        "Solver",
        ["PuLP", "OR-Tools", "CVXPY", "Auto-detect"],
        help="Select the optimization solver to use"
    )
    
    # Advanced options
    with st.expander("Advanced Options"):
        max_time = st.slider("Max Solution Time (seconds)", 10, 600, 300)
        show_formulation = st.checkbox("Show Mathematical Formulation", value=False)
        show_logs = st.checkbox("Show Solver Logs", value=False)
    
    st.divider()
    
    # Example problems
    st.header("📚 Example Problems")
    example_category = st.selectbox(
        "Category",
        ["Linear Programming", "Integer Programming", "Transportation", "Assignment", "Scheduling"]
    )
    
    if st.button("Load Example"):
        st.session_state.load_example = True

# Main content area
tab1, tab2, tab3, tab4 = st.tabs(["💡 Solve Problem", "📊 Results", "📈 Visualization", "📖 Help"])

with tab1:
    st.header("Describe Your Problem")
    
    # Problem input
    problem_description = st.text_area(
        "Enter problem description in natural language:",
        height=200,
        placeholder="Example: I need to minimize transportation costs between 3 warehouses and 5 stores. Warehouse 1 has 100 units available...",
        help="Describe your optimization problem. Be specific about objectives, constraints, and data."
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        solve_button = st.button("🚀 Solve Problem", type="primary", use_container_width=True)
    
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if solve_button and problem_description:
        with st.spinner("🤔 Understanding your problem..."):
            try:
                # Step 1: Classify problem
                st.info("**Step 1:** Classifying problem type...")
                # classifier = ProblemClassifier()
                # problem_data = classifier.classify(problem_description)
                
                # Placeholder for development
                st.success("✅ Problem classified as: Linear Programming")
                
                # Step 2: Generate model
                st.info("**Step 2:** Generating mathematical model...")
                # generator = ModelGenerator()
                # model = generator.generate(problem_data)
                
                st.success("✅ Model generated successfully")
                
                # Step 3: Solve
                st.info("**Step 3:** Solving with " + solver_type + "...")
                # solver = SolverInterface(solver_type=solver_type.lower())
                # solution = solver.solve(model, max_time=max_time)
                
                st.success("✅ Solution found!")
                
                # Step 4: Interpret
                st.info("**Step 4:** Interpreting results...")
                # interpreter = ResultInterpreter()
                # explanation = interpreter.interpret(solution, problem_data)
                
                st.session_state.solution_ready = True
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Tip: Make sure your problem description is clear and includes all necessary data.")
    
    elif solve_button:
        st.warning("⚠️ Please enter a problem description first.")
    
    if clear_button:
        problem_description = ""
        st.rerun()

with tab2:
    st.header("Solution Results")
    
    if 'solution_ready' in st.session_state and st.session_state.solution_ready:
        # Results display
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Objective Value", "$12,450", "Optimal")
            st.metric("Solution Status", "Optimal", delta_color="normal")
            st.metric("Solve Time", "2.3s")
        
        with col2:
            st.metric("Variables", "45")
            st.metric("Constraints", "78")
            st.metric("Iterations", "156")
        
        st.divider()
        
        # AI Explanation
        st.subheader("🤖 AI Explanation")
        st.info("""
        Based on the optimization results, here are the key recommendations:
        
        1. **Optimal Transportation Plan**: Ship 60 units from Warehouse A to Store 1...
        2. **Cost Savings**: This plan saves $3,200 compared to current operations
        3. **Utilization**: All warehouse capacity is efficiently utilized
        
        [Detailed explanation will be generated by AI]
        """)
        
        # Decision Variables
        st.subheader("📋 Decision Variables")
        st.info("Variable values will be displayed here in a table format")
        
        # Export options
        st.download_button(
            "📥 Download Results (CSV)",
            "sample,data",
            "results.csv",
            "text/csv"
        )
    else:
        st.info("👈 Solve a problem to see results here")

with tab3:
    st.header("Visualizations")
    
    if 'solution_ready' in st.session_state and st.session_state.solution_ready:
        viz_type = st.selectbox(
            "Visualization Type",
            ["Network Diagram", "Bar Chart", "Sensitivity Analysis", "Gantt Chart"]
        )
        
        st.info("📊 Visualizations will be displayed here based on problem type")
    else:
        st.info("👈 Solve a problem to see visualizations here")

with tab4:
    st.header("How to Use OR Assistant")
    
    st.markdown("""
    ### 🎯 Getting Started
    
    1. **Describe Your Problem**: Use natural language to describe your optimization problem
    2. **Select Solver**: Choose your preferred solver (or use auto-detect)
    3. **Click Solve**: Let the AI understand, model, and solve your problem
    4. **Review Results**: Get actionable insights and visualizations
    
    ### 📝 Problem Types Supported
    
    - **Linear Programming (LP)**: Optimize linear objectives with linear constraints
    - **Integer Programming (IP)**: Optimization with discrete decision variables
    - **Transportation**: Minimize costs of shipping goods from sources to destinations
    - **Assignment**: Optimally match resources to tasks
    - **Scheduling**: Sequence tasks over time to meet deadlines
    
    ### 💡 Example Problems
    
    **Transportation Problem:**
    ```
    I need to minimize transportation costs between 3 warehouses and 5 stores.
    Warehouse capacities: [100, 150, 120]
    Store demands: [80, 90, 60, 70, 50]
    Costs per unit: [cost matrix here]
    ```
    
    **Production Planning:**
    ```
    Maximize profit from producing 3 products using 2 machines.
    Machine 1 has 480 hours available, Machine 2 has 380 hours.
    Product A: 8 hours on M1, 4 hours on M2, profit $50
    [continue with other products...]
    ```
    
    ### ⚙️ Tips for Best Results
    
    - Be specific about constraints and objectives
    - Include all numerical data
    - Clearly state what you want to minimize or maximize
    - Mention any special requirements (integer values, time windows, etc.)
    
    ### 🆘 Need Help?
    
    - Check the [Documentation](docs/USER_GUIDE.md)
    - See [Examples](data/examples/)
    - Open an issue on GitHub
    """)

# Footer
st.divider()
st.caption("OR Assistant v0.1.0 | Built with AI & Streamlit | NDSU Project")
