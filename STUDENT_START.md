# FOR THE STUDENT: Getting Started

Hello! This repository contains everything you need to build the OR Assistant system. Here's how to get started.

## 📁 What You Have

This repository contains:
- ✅ Complete project structure
- ✅ Starter code for all modules
- ✅ Example problems
- ✅ Test files
- ✅ Documentation
- ✅ Configuration files

## 🚀 First Steps (Do This Today!)

### 1. Set Up Your Environment (30 minutes)

```bash
# Navigate to the project
cd or-assistant

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install everything
pip install -r requirements.txt
```

### 2. Get Your API Key (10 minutes)

Choose one provider:

**Option A - Anthropic Claude:**
1. Go to https://console.anthropic.com
2. Sign up for an account
3. Create an API key
4. Save it somewhere safe!

**Option B - OpenAI:**
1. Go to https://platform.openai.com/api-keys
2. Sign up for an account
3. Create an API key
4. Save it somewhere safe!

### 3. Configure the Project (5 minutes)

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your API key
# Use any text editor (nano, vim, VS Code, etc.)
nano .env
```

Add one of these lines:
```
# For Anthropic
ANTHROPIC_API_KEY=your_anthropic_key_here

# OR for OpenAI
OPENAI_API_KEY=your_openai_key_here
```

### 4. Test That Everything Works (10 minutes)

```bash
# Test the classifier
python src/agents/problem_classifier.py

# Run tests
pytest tests/ -v

# Start the Streamlit app
streamlit run app.py
```

## 📖 What to Read

### Start Here
1. **QUICKSTART.md** - Get running fast
2. **docs/DEVELOPMENT.md** - Your main development guide
3. **docs/USER_GUIDE.md** - Understand what you're building

### Read When Needed
- **CONTRIBUTING.md** - Code style and best practices
- **Individual module files** - Each has examples at the bottom

## 🗓️ Your 12-Week Plan

### Week 1-2: Foundation ✅
**Goal**: Get comfortable with the tools

**Do This**:
1. ✅ Set up environment (done above!)
2. Complete PuLP tutorial: https://coin-or.github.io/pulp/main/index.html
3. Read first 3 chapters
4. Solve 3 example problems manually
5. Understand the code in `src/agents/problem_classifier.py`

**Deliverable**: Run the classifier on 5 different problems and see it work

### Week 3-4: Problem Classification
**Goal**: Master the AI classification system

**Files to Focus On**:
- `src/agents/problem_classifier.py`
- `tests/test_classifier.py`

**Tasks**:
1. Read the classifier code carefully
2. Test with example problems
3. Try to break it - what makes it fail?
4. Add a new problem type
5. Write more tests

**Deliverable**: Classifier that correctly identifies 8+ problem types

### Week 5-7: Model Generation
**Goal**: Build mathematical models

**Files to Focus On**:
- `src/modeling/model_generator.py`
- `tests/test_model_generator.py` (you'll create this)
- `data/examples/` - use these as test cases

**Tasks**:
1. Implement `_generate_lp_model()`
2. Implement `_generate_transportation_model()`
3. Implement `_generate_assignment_model()`
4. Test each one extensively
5. Add validation

**Deliverable**: Working model generators for 5 problem types

### Week 8-9: Solver Integration
**Goal**: Solve problems and get results

**Files to Focus On**:
- `src/solvers/solver_interface.py`
- `tests/test_solver.py`

**Tasks**:
1. Test the existing solver code
2. Try solving 20+ problems
3. Handle edge cases (infeasible, unbounded)
4. Add sensitivity analysis
5. Try adding OR-Tools support (optional)

**Deliverable**: 25+ test problems solved successfully

### Week 10-11: Results & UI
**Goal**: Make it user-friendly

**Files to Focus On**:
- `src/interpreters/result_interpreter.py`
- `app.py`
- `cli.py`

**Tasks**:
1. Improve result interpretation
2. Add visualizations (charts, graphs)
3. Polish Streamlit UI
4. Add export features
5. Test end-to-end workflow

**Deliverable**: Beautiful, working prototype

### Week 12: Final Polish
**Goal**: Demo-ready system

**Tasks**:
1. Fix all known bugs
2. Write remaining tests
3. Complete documentation
4. Create demo presentation
5. Practice your demo

**Deliverable**: Polished system ready to present

## 💻 Daily Coding Workflow

### Every Day (2-3 hours)
```bash
# 1. Pull latest changes (if working with team)
git pull

# 2. Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate

# 3. Pick ONE task from your weekly goals

# 4. Code, test, repeat
# - Write a small piece of code
# - Test it immediately
# - Fix any issues
# - Move to next piece

# 5. Run all tests before finishing
pytest

# 6. Commit your work
git add .
git commit -m "Descriptive message about what you did"
git push
```

## 🆘 When You Get Stuck

### Debugging Steps
1. **Read the error message** - It usually tells you what's wrong
2. **Add print statements** - See what values you're getting
3. **Check the examples** - Look at the test files
4. **Use AI** - Ask AI (Claude or OpenAI) for help debugging
5. **Google it** - Someone has had this error before
6. **Take a break** - Come back with fresh eyes

### Resources
- **PuLP Documentation**: https://coin-or.github.io/pulp/
- **Anthropic Docs**: https://docs.anthropic.com
- **OpenAI Docs**: https://platform.openai.com/docs
- **Streamlit Docs**: https://docs.streamlit.io
- **Stack Overflow**: Search for specific errors

### Getting Help
- If stuck > 2 hours, ask for help
- Create a GitHub issue describing the problem
- Include: what you're trying to do, what error you're getting, what you've tried

## 🎯 Success Criteria

By mid-April, you should have:
- [ ] Working classification system
- [ ] Model generation for 5+ problem types
- [ ] Solver integration
- [ ] Result interpretation
- [ ] Functional UI
- [ ] 50+ passing tests
- [ ] Complete documentation
- [ ] Demo-ready presentation

## ⚡ Pro Tips

### Save Time
1. **Test often** - Don't write 100 lines before testing
2. **Use examples** - Start with the example problems
3. **Read the code** - The starter code has examples
4. **Commit frequently** - Small commits are easier to understand

### Stay Organized
1. **One feature at a time** - Don't try to do everything
2. **Write tests first** - Know what success looks like
3. **Document as you go** - Don't wait until the end
4. **Track your progress** - Check off completed tasks

### Code Quality
1. **Use clear names** - `calculate_cost()` not `calc()`
2. **Add comments** - Explain why, not what
3. **Keep functions small** - One function, one job
4. **Test edge cases** - Empty inputs, negative numbers, etc.

## 🎓 Learning Goals

Beyond the code, you'll learn:
- AI/LLM integration
- Mathematical optimization
- Software architecture
- Testing & debugging
- Documentation
- Version control
- Problem-solving

## 📝 Weekly Progress Tracker

Create a file `PROGRESS.md` and update it weekly:

```markdown
## Week 1 (Jan 20-26)
- [x] Set up environment
- [x] Got API key
- [x] Ran first test
- [ ] Completed PuLP tutorial
- Notes: PuLP is easier than I thought!

## Week 2 (Jan 27-Feb 2)
- [ ] ...
```

## 🎉 You've Got This!

This is a challenging but achievable project. The hardest part is getting started - which you've already done!

Key to success:
- **Code a little every day** (2-3 hours)
- **Test everything** immediately
- **Ask for help** when stuck
- **Stay organized** with your tasks
- **Have fun** - you're building something cool!

Remember: It's okay to not understand everything at first. Keep coding, testing, and learning. You'll get there!

Questions? Open an issue or reach out for help.

Good luck! 🚀

---

**Next Action**: Follow the "First Steps" section above right now. Get your environment set up today!
