export PYTHONPATH=$(shell pwd)

all: deps tests doc

pypi:
	rm -rf dist
	python setup.py sdist
	twine check dist/*
	python -m twine upload dist/*

clean:
	rm -rf dist
	make -C docs clean
	-rm .coverage

run_examples:
	cd examples/graphviz; ./all.py
	cd examples/gephi; ./all.py

deps:
	pip install -r requirements/development.txt
	pip install -r requirements/documentation.txt

tests:
	py.test \
		--ignore=pycallgraph/memory_profiler.py \
		test pycallgraph examples

	coverage run --source pycallgraph,scripts -m pytest
	coverage report -m

	flake8 --exclude=__init__.py,memory_profiler.py pycallgraph
	flake8 --ignore=F403 test
	flake8 examples

doc:
	cd docs/examples && ./generate.py
	cd docs/guide/filtering && ./generate.py

	make -C docs html man
	mv docs/_build/man/pycallgraph.1 man/

