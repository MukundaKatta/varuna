.PHONY: test lint format clean install dev

test:
	PYTHONPATH=src python3 -m pytest tests/ -v --tb=short

lint:
	python3 -m py_compile src/varuna/core.py
	python3 -m py_compile src/varuna/parser.py
	python3 -m py_compile src/varuna/scheduler.py

format:
	python3 -m black src/ tests/ 2>/dev/null || true

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache build dist *.egg-info

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
