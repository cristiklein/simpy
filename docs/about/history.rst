==========================
SimPy History & Change Log
==========================

SimPy was originally based on ideas from Simula and Simscript but uses standard
Python. It combines two previous packages, SiPy, in Simula-Style (Klaus Müller)
and SimPy, in Simscript style (Tony Vignaux and Chang Chui).

SimPy was based on efficient implementation of co-routines using Python's
generators capability.

SimPy 3 introduced a completely new API but still relied on Python's generators
as they proved to work very well.

The package has been hosted on Sourceforge.net since September 15th,  2002.
In June 2012, the project moved to Bitbucket.org.


2013: Version 3.0
=================

- Completely rewritten from scratch.
- Greatly simplified API and code base.
- Stronger focus on events. Processes yield events and thus start waiting for
  them. There are simple events, timeouts and even processes are now events
  (you can wait until a process terminates).
- SimPy can now be used for multi-agent systems (with real or simulated
  communication) or other event-loop based applications more easily.
- Removed plotting and GUI capabilities. *Pyside* and *matplotlib* are much
  better with this.


December 2011: Version 2.3
==========================

- Support for Python 3.x has been added
- Examples and tutorials modified to run on Python 2.6 and up
  including Python 3.
- Examples can now be executed via py.test so we can make sure they do run.
- The documentation has had some reorganisation. The index has had
  work done on it. The Simple manual has been pulled out and is setup
  as a separate manual.


September 2011: Version 2.2
===========================

- The Unit tests have been rewritten.
- The directory sturcture of the release has been simplified
- The documentation has had some minor changes


May 2010: Version 2.1.0
=======================

A major release of SimPy, with a new code base, a (small) number of
additions to the API, and added documentation.

Additions
~~~~~~~~~

- A function `step` has been added to the API. When called, it executes
  the next scheduled event. (`step` is actually a method of Simulation.)
- Another new function is `peek`. It returns the time of the next event.
  By using `peek` and `step` together, one can easily write e.g. an
  interactive program to step through a simulation event by event.
- A simple interactive debugger ``stepping.py`` has been added. It allows
  stepping through a simulation, with options to skip to a certain time,
  skip to the next event of a given process, or viewing the event list.
- Versions of the Bank tutorials (documents and programs) using the advanced
  object-oriented API have been added.
- A new document describes tools for gaining insight into and debugging SimPy
  models.

Changes
~~~~~~~~~~

- Major re-structuring of SimPy code, resulting in much less
  SimPy code -- great for the maintainers.
- Checks have been added which test whether entities belong to the
  same `Simulation` instance.
- The `Monitor` and `Tally` methods `timeAverage` and `timeVariance`
  now calculate only with the observed time-series. No value is
  assumed for the period prior to the first observation.
- Changed class `Lister` so that circular references between
  objects no longer lead to stack overflow and crash.

Repairs
~~~~~~~

- Functions `allEventNotices` and `allEventTimes` are working again.
- Error messages for methods in SimPy.Lib work again.


April 2009: Release 2.0.1
=========================

A bug-fix release of SimPy 2.0


October 2008: Version 2.0
=========================

This is a major release with changes to the SimPy application programming
interface (API) and the formatting of the documentation.

API changes
~~~~~~~~~~~~~~~

In addition to its existing API, SimPy now also has an object oriented API.
The additional API

- allows running SimPy in parallel on multiple processors or multi-core CPUs,
- supports better structuring of SimPy programs,
- allows subclassing of class *Simulation* and thus provides users with
  the capability of creating new simulation modes/libraries like SimulationTrace, and
- reduces the total amount of SimPy code, thereby making it easier to maintain.

Note that the OO API is **in addition** to the old API. SimPy 2.0 is fully
backward compatible.

Documentation format changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SimPy's documentation has been restructured and processed by the Sphinx
documentation generation tool. This has generated one coherent, well
structured document which can be easily browsed. A seach capability is included.


March 2008: Version 1.9.1
==========================

This is a bug-fix release which cures the following bugs:

- Excessive production of circular garbage, due to a circular reference
  between Process instances and event notices. This led to large memory
  requirements.

- Runtime error for preempts of proceeses holding multiple Resource objects.

It also adds a Short Manual, describing only the basic facilities of SimPy.

December 2007: Version 1.9
==========================

This is a major release with added functionality/new user API calls and bug fixes.

Major changes
~~~~~~~~~~~~~

- The event list handling has been changed to improve the runtime performance
  of large SimPy models (models with thousands of processes). The use of
  dictionaries for timestamps has been stopped. Thanks are due to Prof.
  Norm Matloff and a team of his students who did a study on improving
  SimPy performance. This was one of their recommendations. Thanks, Norm and guys!
  Furthermore, in version 1.9 the 'heapq' sorting package replaces 'bisect'.
  Finally, cancelling events no longer removes them, but rather marks them.
  When their event time comes, they are ignored. This was Tony Vignaux' idea!

- The Manual has been edited and given an easier-to-read layout.

- The Bank2 tutorial has been extended by models  which use more advanced
  SimPy commands/constructs.

Bug fixes
~~~~~~~~~

- The tracing of 'activate' statements has been enabled.

Additions
~~~~~~~~~

- A method returning the time-weighted variance of observations
  has been added to classes Monitor and Tally.

- A shortcut activation method called "start" has been added
  to class Process.


January 2007: Version 1.8
=========================


Major Changes
~~~~~~~~~~~~~~

- SimPy 1.8 and future releases will not run under the obsolete
  Python 2.2 version. They require Python 2.3 or later.

- The Manual has been thoroughly edited, restructured and rewritten.
  It is now also provided in PDF format.

- The Cheatsheet has been totally rewritten in a tabular format.
  It is provided in both XLS (MS Excel spreadsheet) and PDF format.

- The version of SimPy.Simulation(RT/Trace/Step) is now accessible
  by the variable 'version'.

- The *__str__* method of Histogram was changed to return a table format.

Bug fixes
~~~~~~~~~~~~

- Repaired a bug in *yield waituntil* runtime code.

- Introduced check for *capacity* parameter of a Level or a Store
  being a number > 0.

- Added code so that self.eventsFired gets set correctly after an event fires
  in a compound yield get/put with a waitevent clause (reneging case).

- Repaired a bug in prettyprinting of Store objects.

Additions
~~~~~~~~~~

- New compound yield statements support time-out or event-based
  reneging in get and put operations on Store and Level instances.

- *yield get* on a Store instance can now have a filter function.

- All Monitor and Tally instances are automatically registered in list
  *allMonitors* and *allTallies*, respectively.

- The new function *startCollection* allows activation of Monitors and
  Tallies at a specified time.

- A *printHistogram* method was added to Tally and Monitor which generates
  a table-form histogram.

- In SimPy.SimulationRT: A function for allowing changing
  the ratio wall clock time to simulation time has been added.

June 2006: Version 1.7.1
==============================

This is a maintenance release. The API has not been changed/added to.

-   Repair of a bug in the _get methods of Store and Level which could lead to synchronization problems
    (blocking of producer processes, despite space being available in the buffer).

-   Repair of Level __init__ method to allow initialBuffered to be of either float or int type.

-   Addition of type test for Level get parameter 'nrToGet' to limit it to positive
    int or float.

-   To improve pretty-printed output of 'Level' objects, changed attribute
    '_nrBuffered' to 'nrBuffered' (synonym for 'amount' property).

-   To improve pretty-printed output of 'Store' objects, added attribute
    'buffered' (which refers to '_theBuffer' attribute).


February 2006: Version 1.7
===============================

This is a major release.

- Addition of an abstract class Buffer, with two sub-classes *Store* and *Level*
  Buffers are used for modelling inter-process synchronization in producer/
  consumer and multi-process cooperation scenarios.

- Addition of two new *yield* statements:

  + *yield put* for putting items into a buffer, and

  + *yield get* for getting items from a buffer.

- The Manual has undergone a major re-write/edit.

- All scripts have been restructured for compatibility with IronPython 1 beta2.
  This was doen by moving all *import* statements to the beginning of the scripts.
  After the removal of the first (shebang) line, all scripts (with the exception
  of plotting and GUI scripts) can run successfully under this new Python
  implementation.

September 2005: Version 1.6.1
=================================

This is a minor release.

- Addition of Tally data collection class as alternative
  to Monitor. It is intended for collecting very large data sets
  more efficiently in storage space and time than Monitor.

- Change of Resource to work with Tally (new Resource
  API is backwards-compatible with 1.6).

- Addition of function setHistogram to class Monitor for initializing
  histograms.

- New function allEventNotices() for debugging/teaching purposes. It returns
  a prettyprinted string with event times and names of process instances.

- Addition of function allEventTimes (returns event times of all scheduled
  events).

15 June 2005: Version 1.6
==============================

- Addition of two compound yield statement forms to support the modelling of
  processes reneging from resource queues.

- Addition of two test/demo files showing the use of the new reneging statements.

- Addition of test for prior simulation initialization in method activate().

- Repair of bug in monitoring thw waitQ of a resource when preemption occurs.

- Major restructuring/editing to Manual and Cheatsheet.

1 February 2005: Version 1.5.1
==================================

- MAJOR LICENSE CHANGE:

	Starting with this version 1.5.1, SimPy is being release under the GNU
	Lesser General Public License (LGPL), instead of the GNU GPL. This change
	has been made to encourage commercial firms to use SimPy in for-profit
	work.

- Minor re-release

- No additional/changed functionality

- Includes unit test file'MonitorTest.py' which had been accidentally deleted
  from 1.5

- Provides updated version of 'Bank.html' tutorial.

- Provides an additional tutorial ('Bank2.html') which shows
  how to use the new synchronization constructs introduced in SimPy 1.5.

- More logical, cleaner version numbering in files.

1 December 2004: Version 1.5
================================

- No new functionality/API changes relative to 1.5 alpha

- Repaired bug related to waiting/queuing for multiple events

- SimulationRT: Improved synchronization with wallclock time on Unix/Linux

25 September 2004: Version 1.5alpha
===================================

- New functionality/API additions

	* SimEvents and signalling synchronization constructs, with 'yield waitevent' and 'yield queueevent' commands.

	* A general "wait until" synchronization construct, with the 'yield waituntil' command.

- No changes to 1.4.x API, i.e., existing code will work as before.

19 May 2004: Version 1.4.2
==========================

- Sub-release to repair two bugs:

	* The unittest for monitored Resource queues does not fail anymore.

	* SimulationTrace now works correctly with "yield hold,self" form.

- No functional or API changes

29 February 2004: Version 1.4.1
===============================

- Sub-release to repair two bugs:

     * The (optional) monitoring of the activeQ in Resource now works correctly.

     * The "cellphone.py" example is now implemented correctly.

- No functional or API changes

1 February 2004: Version 1.4
============================

- Released on SourceForge.net


22 December 2003: Version 1.4 alpha
===================================

- New functionality/API changes

	* All classes in the SimPy API are now new style classes, i.e., they inherit from *object* either directly or indirectly.

	* Module *Monitor.py* has been merged into module *Simulation.py* and all *SimulationXXX.py* modules. Import of *Simulation* or any *SimulationXXX* module now also imports *Monitor*.

	* Some *Monitor* methods/attributes have changed. See Manual!

	* *Monitor* now inherits from *list*.

      * A class *Histogram* has been added to *Simulation.py* and all *SimulationXXX.py* modules.

      * A module *SimulationRT* has been added which allows synchronization between simulated and wallclock time.

      * A moduleSimulationStep which allows the execution of a simulation model event-by-event, with the facility to execute application code after each event.

      * A Tk/Tkinter-based module *SimGUI* has been added which provides a SimPy GUI framework.

      * A Tk/Tkinter-based module *SimPlot* has been added which provides for plot output from SimPy programs.


22 June 2003: Version 1.3
=========================

- No functional or API changes
- Reduction of sourcecode linelength in Simulation.py to <= 80 characters


June 2003: Version 1.3 alpha
============================

- Significantly improved performance
- Significant increase in number of quasi-parallel processes SimPy can handle
- New functionality/API changes:

	* Addition of SimulationTrace, an event trace utility
	* Addition of Lister, a prettyprinter for instance attributes
	* No API changes

- Internal changes:

	* Implementation of a proposal by Simon Frost: storing the keys of the event set dictionary in a binary search tree using bisect. Thank you, Simon! SimPy 1.3 is dedicated to you!

- Update of Manual to address tracing.
- Update of Interfacing doc to address output visualization using Scientific Python gplt package.


29 April 2003: Version 1.2
==========================

- No changes in API.
- Internal changes:
	* Defined "True" and "False" in Simulation.py to support Python 2.2.


22 October 2002
===============

-   Re-release of 0.5 Beta on SourceForge.net to replace corrupted file __init__.py.
-   No code changes whatever!


18 October 2002
===============

-   Version 0.5 Beta-release, intended to get testing by application developers and system integrators in preparation of first full (production) release. Released on SourceForge.net on 20 October 2002.
-   More models
-   Documentation enhanced by a manual, a tutorial ("The Bank") and installation instructions.
-   Major changes to the API:

    *  Introduced 'simulate(until=0)' instead of 'scheduler(till=0)'. Left 'scheduler()' in for backward compatibility, but marked as deprecated.
    *  Added attribute "name" to class Process. Process constructor is now::

       	def __init__(self,name="a_process")

       Backward compatible if keyword parameters used.

    *  Changed Resource constructor to::

       	def __init__(self,capacity=1,name="a_resource",unitName="units")

       Backward compatible if keyword parameters used.


27 September 2002
=================

* Version 0.2 Alpha-release, intended to attract feedback from users
* Extended list of models
* Upodated documentation

17 September 2002
=================

* Version 0.1.2 published on SourceForge; fully working, pre-alpha code
* Implements simulation, shared resources with queuing (FIFO), and monitors
  for data gathering/analysis.
* Contains basic documentation (cheatsheet) and simulation models for test and
  demonstration.
