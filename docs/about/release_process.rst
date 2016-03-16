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

#. Update the version number in :file:`simpy/__init__.py` and commit:

   .. code-block:: bash

    $ hg ci -m 'Bump version from x.y.z to a.b.c'

   .. warning::

      Do not yet tag and push the changes so that you can safely do a rollback
      if one of the next step fails and you need change something!

#. Write a draft for the announcement mail with a list of changes,
   acknowledgements and installation instructions. Everyone in the team should
   agree with it.


Build and release
=================

#. Test the release process. Build a source distribution and a `wheel
   <https://pypi.python.org/pypi/wheel>`_ package and test them:

   .. code-block:: bash

    $ python setup.py sdist bdist_wheel
    $ ls dist/
    simpy-a.b.c-py2.py3-none-any.whl simpy-a.b.c.tar.gz

   Try installing them:

   .. code-block:: bash

    $ rm -rf /tmp/simpy-sdist  # ensure clean state if ran repeatedly
    $ virtualenv /tmp/simpy-sdist
    $ /tmp/simpy-sdist/bin/pip install pytest
    $ /tmp/simpy-sdist/bin/pip install dist/simpy-a.b.c.tar.gz
    $ /tmp/simpy-sdist/bin/python
    >>> import simpy  # doctest: +SKIP
    >>> simpy.__version__  # doctest: +SKIP
    'a.b.c'
    >>> simpy.test()  # doctest: +SKIP

   and

   .. code-block:: bash

    $ rm -rf /tmp/simpy-wheel  # ensure clean state if ran repeatedly
    $ virtualenv /tmp/simpy-wheel
    $ /tmp/simpy-wheel/bin/pip install pytest
    $ /tmp/simpy-wheel/bin/pip install dist/simpy-a.b.c-py2.py3-none-any.whl
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

#. Upload the distributions for the new version to the test server and test the
   installation again:

   .. code-block:: bash

    $ twine upload -r test dist/simpy*a.b.c*
    $ pip install -i https://testpypi.python.org/pypi simpy

#. Check if the package is displayed correctly:
   https://testpypi.python.org/pypi/simpy

#. Finally upload the package to PyPI and test its installation one last time:

   .. code-block:: bash

    $ twine upload -r pypi dist/simpy*a.b.c*
    $ pip install -U simpy

#. Check if the package is displayed correctly:
   https://pypi.python.org/pypi/simpy


Post release
============

#. Push your changes:

   .. code-block:: bash

    $ hg tag a.b.c
    $ hg push ssh://hg@bitbucket.org/simpy/simpy

#. Activate the `documentation build
   <https://readthedocs.org/dashboard/simpy/versions/>`_ for the new version.

#. Send the prepared email to the mailing list and post it on Google+.

#. Update `Wikipedia <http://en.wikipedia.org/wiki/SimPy>`_ entries.

#. Update `Python Wiki
   <https://wiki.python.org/moin/UsefulModules#Scientific>`_

#. Post something to Planet Python (e.g., via Stefan's blog).
