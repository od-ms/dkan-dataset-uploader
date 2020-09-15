lint: 
	pylint --rcfile=setup.cfg **/*.py
	flake8 .

