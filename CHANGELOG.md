# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- OpenAI API support - users can now use either Anthropic Claude or OpenAI models
- Unified API client (`src/utils/api_client.py`) for seamless provider switching
- Auto-detection of available API keys
- `AI_PROVIDER` environment variable to force a specific provider
- Updated all documentation to reflect multi-provider support

### Planned
- Simulation engine integration
- Advanced scheduling algorithms
- Multi-objective optimization
- Stochastic programming support
- Web API deployment
- User authentication
- Saved problem templates

## [0.1.0] - 2025-01-20

### Added
- Initial project structure
- Problem classification using Claude AI
- Model generation for LP, IP, Transportation, Assignment
- Solver interface for PuLP
- Result interpretation with Claude AI
- Streamlit web interface
- CLI interface
- Basic visualizations
- Example problems
- Unit and integration tests
- Documentation (User Guide, Development Guide)

### In Progress
- Sensitivity analysis features
- OR-Tools integration
- Enhanced visualizations
- More problem type support

## Project Milestones

### Phase 1: Foundation (Weeks 1-2) ✅
- Environment setup
- Basic architecture
- AI API integration (Anthropic Claude and OpenAI)

### Phase 2: Core Features (Weeks 3-9) 🚧
- Problem classification
- Model generation
- Solver integration

### Phase 3: Enhancement (Weeks 10-11) 📋
- Result interpretation
- UI polish
- Visualizations

### Phase 4: Finalization (Week 12) 📋
- Testing
- Documentation
- Demo preparation

---

## Version History

### Version 0.1.0 (Current)
**Status**: Development
**Release Date**: TBD (Mid-April 2025)
**Key Features**:
- AI-powered problem understanding
- Automatic model formulation
- Multi-solver support
- Natural language results

### Future Versions

#### Version 0.2.0 (Planned)
- Simulation capabilities
- Advanced scheduling
- Custom algorithm upload
- Enhanced visualizations

#### Version 1.0.0 (Future)
- Production-ready release
- Full documentation
- Commercial solver integration
- API deployment
- User management
