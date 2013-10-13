===============
Release Process
===============

This process describes the steps to execute in order to release a new version
of SimPy.


Preparations
============

#. Close all `tickets for the next version
   <https://bitbucket.org/simpy/simpy/issues?status=new&status=open>`_.

#. Update the *minium* required versions of dependencies in :file:`setup.py`.
   Update the *exact* version of all entries in :file:`requirements.txt`.

#. Run :command:`tox` from the project root. All tests for all supported
   versions must pass:

   .. code-block:: bash

    $ tox
    [...]
    ________ summary ________
    py27: commands succeeded
    py32: commands succeeded
    py33: commands succeeded
    pypy: commands succeeded
    congratulations :)

   .. note::

    Tox will use the :file:`requirements.txt` to setup the venvs, so make sure
    you've updated it!

#. Build the docs (HTML is enough). Make sure there are no errors and undefined
   references.

   .. code-block:: bash

    $ cd docs/
    $ make clean html
    $ cd ..

#. Check if all authors are listed in :file:`AUTHORS.txt`.

#. Update the change logs (:file:`CHANGES.txt` and
   :file:`docs/about/history.rst`). Only keep changes for the current major
   release in :file:`CHANGES.txt` and reference the history page from there.

#. Commit all changes:

   .. code-block:: bash

    $ hg ci -m 'Updated change log for the upcoming release.'

#. Write a draft for the announcement mail with a list of changes,
   acknowledgements and installation instructions. Everyone in the team should
   agree with it.


Build and release
=================

#. Test the release process. Build a source distribution and a `wheel
   <https://pypi.python.org/pypi/wheel>`_ package and test them:

   .. code-block:: bash

    $ python setup.py sdist
    $ python setup.py bdist_wheel
    $ ls dist/
    simpy-a.b.c-py2.py3-none-any.whl simpy-a.b.c.tar.gz

   Try installing them:

   .. code-block:: bash

    $ rm -rf /tmp/simpy-sdist  # ensure clean state if ran repeatedly
    $ virtualenv /tmp/simpy-sdist
    $ /tmp/simpy-sdist/bin/pip install pytest
    $ /tmp/simpy-sdist/bin/pip install --no-index dist/simpy-a.b.c.tar.gz
    $ /tmp/simpy-sdist/bin/python
    >>> import simpy
    >>> simpy.__version__  # doctest: +SKIP
    'a.b.c'
    >>> simpy.test()  # doctest: +SKIP

   and

   .. code-block:: bash

    $ rm -rf /tmp/simpy-wheel  # ensure clean state if ran repeatedly
    $ virtualenv /tmp/simpy-wheel
    $ /tmp/simpy-wheel/bin/pip install pytest
    $ /tmp/simpy-wheel/bin/pip install --use-wheel --no-index --find-links dist simpy
    $ /tmp/simpy-wheel/bin/python
    >>> import simpy  # doctest: +SKIP
    >>> simpy.__version__  # doctest: +SKIP
    'a.b.c'
    >>> simpy.test()  # doctest: +SKIP

#. Create or check your accounts for the `test server
   <https://testpypi.python.org/pypi>` and `PyPI
   <https://pypi.python.org/pypi>`_. Update your :file:`~/.pypirc` with your
   current credentials:

   .. code-block:: ini

    [distutils]
    index-servers =
        pypi
        test

    [test]
    repository = https://testpypi.python.org/pypi
    username = <your test user name goes here>
    password = <your test password goes here>

    [pypi]
    repository = http://pypi.python.org/pypi
    username = <your production user name goes here>
    password = <your production password goes here>

#. Register SimPy with the test server and upload the distributions:

   .. code-block:: bash

    $ python setup.py register -r test
    $ python setup.py sdist upload -r test
    $ python setup.py bdist_wheel upload -r test

#. Check if the package is displayed correctly:
   https://testpypi.python.org/pypi/simpy

#. Test the installation again:

   .. code-block:: bash

    $ pip install -i https://testpypi.python.org/pypi simpy

#. Update the version number in :file:`simpy/__init__.py`, commit and create
   a tag:

   .. code-block:: bash

    $ hg ci -m 'Bump version from a.b.c to x.y.z'
    $ hg tag x.y.z
    $ hg push ssh://hg@bitbucket.org/simpy/simpy

#. Finally upload the package to PyPI and test its installation one last time:

   .. code-block:: bash

    $ python setup.py register
    $ python setup.py sdist upload
    $ python setup.py bdist_wheel upload
    $ pip install simpy

#. Check if the package is displayed correctly:
   https://pypi.python.org/pypi/simpy

#. Activate the `documentation build
   <https://readthedocs.org/dashboard/simpy/versions/>`_ for the new version.


Post release
============

#. Send the prepared email to the mailing list and post it on Google+.

#. Update `Wikipedia <http://en.wikipedia.org/wiki/SimPy>`_ entries.

#. Update `Python Wiki
   <https://wiki.python.org/moin/UsefulModules#Scientific>`_

#. Post something to Planet Python (e.g., via Stefan's blog).
