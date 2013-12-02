#######################################
# This file is part of pyCMBS
#######################################

PEP = /home/m300028/shared/dev/svn/pep8/pep8/pep8.py

clean :
	find . -name "*.pyc" -exec rm -rf {} \;
	rm -rf build
	rm -rf MANIFEST

dist : clean
	python setup.py sdist

pep8 :
	$(PEP) ./pyCMBS/netcdf.py
	$(PEP) ./pyCMBS/icon.py
	#$(PEP) ./pyCMBS/grid.py
	#$(PEP) ./pyCMBS/report.py
	#$(PEP) ./pyCMBS/statistic.py
	$(PEP) ./pyCMBS/region.py
	$(PEP) ./pyCMBS/framework/__init__.py
	$(PEP) ./pyCMBS/framework/utils.py
	$(PEP) ./pyCMBS/diagnostic.py
	#diagnstic.py, data.py models.py analysis.py pycmbs.py

