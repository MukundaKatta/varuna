# Contributing to Varuna

## Getting Started

1. Clone the repository
2. Run tests: `make test`
3. Make your changes on a feature branch

## Development

```bash
# Run tests
PYTHONPATH=src python3 -m pytest tests/ -v --tb=short

# Or use Make
make test
```

## Code Style

- Follow PEP 8 conventions
- Use type annotations for all public APIs
- Write docstrings for classes and public methods
- Keep modules focused on a single responsibility

## Testing

- All new features must include tests
- Maintain 22+ test minimum across the suite
- Tests should not require network access or external dependencies

## Pull Requests

1. Create a feature branch from `main`
2. Add tests for new functionality
3. Ensure all tests pass
4. Submit a PR with a clear description
