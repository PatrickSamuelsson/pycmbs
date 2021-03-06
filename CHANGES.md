version 1.0.9
=============
Major further developments and improvements have been made. No full tracking of changes was done. Additional features include e.g.

o geostatistical analysis
o several bugfixes
o increased performance

version 1.0.0
=============
A huge amount of changes have been applied to the code for the release of v1.0.0.

This includes also the change from SVN server to GIT and move of the development
repository to github.

Thus changes made during the last release are not documented completely here, but major differences are the following:
* complete recoding of map plotting functionality using object oriented
  approach
* support of CARTOPY as a plotting backend
* PEP8 compliance of whole project
* several major bugfixes
* restructuring of code
* much better code testing (even if coverage not complete yet)
* ...


version 0.1.6
=============
* implementation of Hodrick-Prescott filter for *Data* object

version 0.1.5 (=rev 513)
========================
o adapted calculation of error index of Gleckler et al. (2008) to account for temporal weighting
o file structure was revised to be more compliant with python standards
o installation using distutils is now possible, using simply 'python setup.py install'
o implemented flexible netCDF I/O handler (currently works only with Nio, but should work with netCDF module in the future)
o improvement of report layout and automatic compilation enabled
o name of analysis scripts is now specified in external file in the configuration directory
o benchmarking now independent from core pyCMBS installation. When pycmbs.py is executable and proper PATH variables are set, then the framework can be executed from everywhere!
o pycmbs.py init --> generates now a template environment for benchmarking; documentation has adapted accordingly
o implementation of new dataset(s) for evaluation of land surface evaporation from the GEWEX LandFluxEVAL project
o implementation of diagnostics for RegionalAnalysis, which allows to calculated for each region standard statistics as well as relationship between two variables.

version 0.1.4 (=rev 405)
========================
o This version is the reference version for the EvaCliMod project
o major improvements of reporting functionalities as needed for EvaClimod project
o added new functionality in GlecklerPlot class to plor errors and ranked errors
o several major bugfixes in the timeconversion in different parts of the code to be compliant with new calendar handling functionality
o implemented standard analysis for surface_radiation_flux
o implementation of a ModelMean class to handle multimodel mean datasets
o implemented standard analysis for SIS analysis
o implemented additional datasets for ocean surface fluxes
o removal of pyCDO
o implemented more robust calculation of cell_area (using temp. directories if no write access to data directory)
o automatic logging of errors in the Data class (uses environment variable)
o implemented mindate/maxdate for Data object

version 0.1.3
=============
o albedo analysis for VIS and NIR separately for JSBACH raw output
o bugfix with datetime conversion for GlobalMean plot.
o proper implementation of multimodel mean
o implemented Data.date to allow for an easier access to date from a Data object using datetime.datetime
o implemented standard analysis of variable: surface_upward_flux

version 0.1.2 (=rev274)
=======================
o implemented new class JSBACH_RAW2, which automatically preprocessed JSBACH and ECHAM output from different (yearly) files
o removed dependencies from old pyCDO module which is supposed to be obsolete and will be removed in the future
o applied several bugfixes
o changed name of main routine for benchmarking from main.py to pycmbs.py
o handling of generation of temporary files in case that directory is write protected. Then temporary data is written to temp directory specified by the system

version 0.1.1 (= rev258)
========================
o path of INI files can now be specified explicitely in benchmarking framework
o implemented automatic calculation of land-sea masks using CDO operator topo on-the-fly.
o implementation of sea-ice analysis in benchmarking framework
o novel operator areasum() for data objet to perform weighted average calculations
o novel functionality to specify remapping method and target grids for remapping in the benchmarking framework
o implemented much more flexibility for configuring report.
o implemented support for different calendars using netcdftime library provided in netCDF4 library. COPYRIGHT has been
  changed accordingly. Note that a major refactoring was needed for that purpose.
  NOTE all files written with older versions pyCMBS might now show a timeshift of one day! This is due to
  an artefact in the pylab num2date/date2num functions which provide the number of days relative to 0001-01-01 *PLUS ONE*
  (see num2date documentation). The new routines have not this artefact.
  Do allow for backward compability with v0.1.0, an option 'oldtime' has been added to Data object, which mimics the old
  behavior.
o initial support for ICON generic unstructured grid. There are still some workarounds for plotting the unstructured data,
  but in general it works well.
o added option to show values in Gleckler Plot in different colors

version 0.1.0 (= rev240)
========================
o initial version released with major data analysis and benchmarking features already included
