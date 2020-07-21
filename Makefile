.PHONY: test clean_coverage test_coverage

test:
	PYTHONPATH=. pytest test/unit
	PYTHONPATH=. test/integration/test-multiprocessing.sh
	PYTHONPATH=.:test/integration test/integration/test-ray.sh

clean_coverage:
	rm -f .coverage

test_coverage: clean_coverage
	PYTHONPATH=. pytest --cov-report= --cov-append --cov paramsurvey -v -v test/unit
	COVERAGE=1 PYTHONPATH=. test/integration/test-multiprocessing.sh test/integration
	COVERAGE=1 PYTHONPATH=.:test/integration test/integration/test-ray.sh test/integration

test_coverage_verbose:
	PARAMSURVEY_VERBOSE=2 COVERAGE=1 PYTHONPATH=. test/integration/test-multiprocessing.sh test/integration
	PARAMSURVEY_VERBOSE=2 COVERAGE=1 PYTHONPATH=.:test/integration test/integration/test-ray.sh test/integration

distclean:
	rm -rf dist/

dist: distclean
	echo "reminder, you must have tagged this commit or you'll end up failing"
	echo "  git tag v0.x.x"
	echo "  git push --tags"
	python ./setup.py sdist
	twine check dist/*
	twine upload dist/* -r pypi
