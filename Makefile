.PHONY: test test-clean

test:
	python3 -m pytest tests/ -v

test-clean:
	python3 -m pytest tests/ --cov=tools --cov-report=term --cov-report=html:coverage_html
