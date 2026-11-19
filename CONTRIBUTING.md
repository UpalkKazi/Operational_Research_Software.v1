# Contributing to OR Assistant

Thank you for your interest in contributing to OR Assistant! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

We welcome feature suggestions! Please:
- Check existing issues first
- Explain the use case
- Describe the proposed solution
- Consider implementation complexity

### Submitting Code

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes**
4. **Write/update tests**
5. **Ensure tests pass**: `pytest`
6. **Update documentation** if needed
7. **Commit with clear messages**
8. **Push to your fork**
9. **Open a Pull Request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/or-assistant.git
cd or-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Code Style

### Python
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

### Formatting
We use `black` for code formatting:
```bash
black src/ tests/
```

### Linting
We use `flake8` for linting:
```bash
flake8 src/ tests/
```

## Testing

### Writing Tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use pytest fixtures for common setup
- Aim for >80% code coverage

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Specific file
pytest tests/test_classifier.py

# Skip integration tests
pytest -m "not integration"
```

## Documentation

### Docstrings
Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When input is invalid
    """
    pass
```

### Comments
- Explain "why", not "what"
- Use clear, concise language
- Update comments when code changes

## Commit Messages

Format:
```
type: brief description

Longer explanation if needed.

Fixes #issue-number
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks

Examples:
```
feat: add knapsack problem support

Implement model generator and solver interface for
knapsack problems with capacity constraints.

Fixes #42
```

```
fix: handle empty problem descriptions

Add validation to check for empty input before
calling classifier API.

Fixes #55
```

## Pull Request Process

1. **Update documentation** if you changed functionality
2. **Add tests** for new features
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** with your changes
5. **Request review** from maintainers

### PR Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts

## Project Structure

Please maintain the existing structure:
```
src/
├── agents/         # AI-related code
├── modeling/       # Model generation
├── solvers/        # Solver interfaces
├── interpreters/   # Result interpretation
├── simulation/     # Simulation (future)
└── utils/          # Utilities
```

## Adding New Problem Types

To add a new problem type:

1. Update `PROBLEM_TYPES` in `src/agents/problem_classifier.py`
2. Add generator method in `src/modeling/model_generator.py`
3. Add template in `src/agents/problem_classifier.py`
4. Create example in `data/examples/`
5. Write tests in `tests/`
6. Update documentation

## Questions?

- Open an issue for questions
- Tag as "question"
- We'll respond within 48 hours

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other unprofessional conduct

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to OR Assistant!
