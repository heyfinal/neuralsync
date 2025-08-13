# Contributing to NeuralSync

Thank you for your interest in contributing to NeuralSync! We welcome contributions from developers, researchers, and AI enthusiasts worldwide. This document provides guidelines and information for contributing to the project.

## 🌟 Ways to Contribute

There are many ways to contribute to NeuralSync:

### 💻 Code Contributions
- **Bug Fixes**: Fix issues and improve stability
- **New Features**: Add new capabilities and tools
- **Performance Improvements**: Optimize existing code
- **Agent Development**: Create new AI agent templates
- **MCP Integrations**: Build new Model Context Protocol servers

### 📚 Documentation
- **Improve Existing Docs**: Fix errors, add clarity, update examples
- **Write Tutorials**: Create step-by-step guides for common tasks
- **API Documentation**: Document new endpoints and methods
- **Architecture Guides**: Explain system components and design decisions

### 🧪 Testing & Quality Assurance
- **Bug Reports**: Identify and report issues
- **Test Coverage**: Write unit and integration tests
- **Performance Testing**: Benchmark and optimize performance
- **Security Testing**: Identify security vulnerabilities

### 🎨 Design & UX
- **Web Dashboard**: Improve the management interface
- **CLI Experience**: Enhance command-line tools
- **Documentation Design**: Make docs more readable and accessible
- **Visualizations**: Create system monitoring dashboards

### 🌐 Community
- **Help Others**: Answer questions in discussions and issues
- **Create Examples**: Build sample applications and use cases
- **Share Knowledge**: Write blog posts, give talks, create videos
- **Translation**: Help translate documentation to other languages

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.9+** installed
- **Docker and Docker Compose** for running services
- **Git** for version control
- **Node.js 18+** (for frontend development)
- **Basic understanding** of AI systems and distributed architectures

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub
   git clone https://github.com/YOUR_USERNAME/neuralsync.git
   cd neuralsync
   ```

2. **Set Up Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

3. **Start Development Services**
   ```bash
   # Start the development stack
   ./neuralsync.sh install
   ./neuralsync.sh start
   
   # Verify everything is running
   ./neuralsync.sh status
   ```

4. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

### Development Workflow

1. **Make Changes**
   - Write your code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

2. **Test Your Changes**
   ```bash
   # Run tests
   pytest tests/
   
   # Run linting
   flake8 neuralsync/
   black neuralsync/
   
   # Type checking
   mypy neuralsync/
   ```

3. **Commit Changes**
   ```bash
   # Stage changes
   git add .
   
   # Commit with descriptive message
   git commit -m "feat: add semantic search optimization
   
   - Implement vector similarity caching
   - Add batch embedding processing
   - Improve query response time by 40%
   
   Fixes #123"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a Pull Request on GitHub with:
   - Clear description of changes
   - Link to related issues
   - Screenshots/demos if applicable

## 📋 Contribution Guidelines

### Code Style

We follow these coding standards:

**Python:**
- **PEP 8** compliance with 88-character line limit
- **Type hints** for all function parameters and returns
- **Docstrings** in Google style for all public functions
- **Import sorting** with isort

```python
from typing import Dict, List, Optional

async def search_memory(
    query: str, 
    limit: int = 10,
    filters: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """Search the memory system using semantic similarity.
    
    Args:
        query: The search query text.
        limit: Maximum number of results to return.
        filters: Optional filters to apply to the search.
        
    Returns:
        List of search results with metadata.
        
    Raises:
        ValueError: If query is empty or invalid.
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Implementation here
    return results
```

**JavaScript/TypeScript:**
- **Prettier** formatting with 2-space indentation
- **ESLint** configuration for consistency
- **TypeScript** for all new frontend code

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(mcp): add support for custom tool definitions

fix(worker): resolve memory leak in embedding generation

docs(api): update search endpoint documentation

test(integration): add end-to-end workflow tests
```

### Pull Request Guidelines

**Before submitting:**
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main

**PR Description should include:**
- **Summary** of changes
- **Motivation** and context
- **Testing** performed
- **Screenshots** (if UI changes)
- **Breaking changes** (if any)
- **Related issues** (link with #123)

### Testing Requirements

All contributions must include appropriate tests:

**Unit Tests:**
```python
import pytest
from neuralsync.memory import MemoryManager

@pytest.mark.asyncio
async def test_memory_search():
    """Test memory search functionality."""
    manager = MemoryManager()
    
    # Test basic search
    results = await manager.search("test query")
    assert isinstance(results, list)
    
    # Test with filters
    filtered_results = await manager.search(
        "test query", 
        filters={"agent": "test-agent"}
    )
    assert len(filtered_results) <= len(results)
```

**Integration Tests:**
```python
@pytest.mark.integration
async def test_agent_communication_workflow():
    """Test complete agent communication workflow."""
    async with test_client() as client:
        # Register agent
        response = await client.post("/agents/register", json={
            "name": "test-agent",
            "provider": "openai",
            "model": "gpt-4"
        })
        assert response.status_code == 200
        
        # Send message
        response = await client.post("/messages/send", json={
            "to_agent": "test-agent",
            "content": "Hello, test!"
        })
        assert response.status_code == 200
```

## 🐛 Bug Reports

When reporting bugs, please include:

### Bug Report Template

```markdown
## Bug Description
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
A clear description of what you expected to happen.

## Screenshots
If applicable, add screenshots to help explain your problem.

## Environment
 - OS: [e.g. macOS 13.5, Ubuntu 22.04]
 - Python Version: [e.g. 3.11.4]
 - NeuralSync Version: [e.g. 1.0.0]
 - Docker Version: [e.g. 24.0.5]

## Additional Context
Add any other context about the problem here.

## Logs
```
Paste relevant logs here
```
```

## 💡 Feature Requests

### Feature Request Template

```markdown
## Is your feature request related to a problem?
A clear and concise description of what the problem is.

## Describe the solution you'd like
A clear and concise description of what you want to happen.

## Describe alternatives you've considered
A clear description of any alternative solutions or features you've considered.

## Use Cases
Describe specific use cases where this feature would be valuable.

## Implementation Ideas
If you have ideas about how this could be implemented, please share them.

## Additional Context
Add any other context, screenshots, or examples about the feature request here.
```

## 🏗️ Architecture Guidelines

When contributing to NeuralSync, follow these architectural principles:

### Design Principles

1. **Modularity**: Components should be loosely coupled and highly cohesive
2. **Scalability**: Design for horizontal scaling and high concurrency
3. **Reliability**: Include comprehensive error handling and recovery
4. **Security**: Follow security best practices, validate all inputs
5. **Observability**: Include logging, metrics, and tracing

### Component Structure

```
neuralsync/
├── services/           # Core services (API, worker, bus)
├── agents/            # Agent templates and implementations
├── mcp/              # Model Context Protocol integration
├── config/           # Configuration management
├── docs/             # Documentation
├── tests/            # Test suites
└── examples/         # Example implementations
```

### API Design

- **RESTful** endpoints for management operations
- **WebSocket** for real-time communication
- **GraphQL** for complex queries (future)
- **Consistent** error responses with proper HTTP status codes
- **Versioning** for backward compatibility

### Database Schema

- **PostgreSQL** for transactional data
- **Qdrant** for vector storage
- **Neo4j** for graph relationships
- **Redis** for caching and queues

## 🔒 Security Guidelines

### Security Best Practices

1. **Input Validation**: Sanitize and validate all user inputs
2. **Authentication**: Use strong authentication mechanisms
3. **Authorization**: Implement proper access controls
4. **Encryption**: Encrypt sensitive data at rest and in transit
5. **Secrets Management**: Never commit secrets to version control

### Reporting Security Issues

Please report security vulnerabilities privately to security@neuralsync.com rather than opening public issues.

## 📖 Documentation Standards

### Documentation Types

1. **API Documentation**: OpenAPI/Swagger specifications
2. **Code Documentation**: Inline comments and docstrings
3. **User Guides**: Step-by-step tutorials
4. **Architecture Docs**: System design and decision records

### Writing Guidelines

- **Clear and Concise**: Use simple language and short sentences
- **Examples**: Include practical examples for all features
- **Consistent**: Follow consistent terminology and formatting
- **Up-to-date**: Update docs when code changes
- **Accessible**: Write for various skill levels

## 🎯 Project Roadmap

### Current Focus Areas

1. **Performance Optimization**: Improve query response times
2. **Agent Templates**: Expand the library of pre-built agents
3. **MCP Integration**: Add more MCP server implementations
4. **Web Dashboard**: Enhanced user interface
5. **Documentation**: Comprehensive guides and tutorials

### Future Directions

- **Multi-modal Support**: Image, audio, and video processing
- **Federated Learning**: Distributed model training
- **Mobile SDKs**: Native mobile app development
- **Enterprise Features**: Advanced security and compliance

## 🏆 Recognition

We value all contributions and recognize contributors through:

- **Contributors Page**: Listed on the project website
- **Release Notes**: Mentioned in release announcements
- **Special Badges**: GitHub profile badges for significant contributors
- **Community Spotlight**: Featured in newsletters and blog posts

## 💬 Communication

### Channels

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time chat and community support
- **Twitter**: Project updates and announcements

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) and help us maintain a positive community.

### Getting Help

- **Documentation**: Check the docs first
- **Discussions**: Ask questions in GitHub Discussions
- **Discord**: Join our community chat
- **Issues**: Create an issue for bugs or feature requests

## 📝 License

By contributing to NeuralSync, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for contributing to NeuralSync! Together, we're building the future of AI orchestration and collaboration. 🚀

For questions about contributing, please reach out in GitHub Discussions or join our Discord community.