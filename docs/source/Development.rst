===========
Development
===========

The preferred way to develop SimPy is by using patchset. These are sent to the
SimPy development mailinglist simpy-dev@lists.sourceforge.net where they can be
peer reviewed by the community. If there are no objections to the patchset, it
is applied to the main repository by the SimPy maintainers. If there are
objections, the patchset needs to be updated to fix these issues before it can
be resend to the mailinglist.

Mercurial is the version control system used in the SimPy project and supports
the management of patchset using the Mercurial Queues extension. The following
sections show a workflow using Mercurial Queues.

Mercurial Queues
================

The Mercurial Queues extension is bundled with Mercurial. However it needs to
be enabled. To do this, edit your ``simpy/.hg/hgrc`` file and add the following
lines:

::

    [extensions]
    mq =


.. note::

    You may also enable the Mercuial Queues extensions globally in ``~/.hgrc``.

Initializing the patch queue
----------------------------

The following command enables the patch queue in your clone of the SimPy
repository:

.. code:: bash

    simpy$ hg qinit

.. note::

    If you work on different machine it may be convenient to manage your
    patches in a repository. By supplying the parameter ``-c`` to the
    ``hg qinit`` command, Mercurial will create a repository for your patches.

Creating patchsets
------------------

After you have enabled patch queues in your repository you can start to work on
your first patch. Start by naming your patch:

.. code:: bash

    simpy$ hg qnew my-first-patch

Now start to hack on the source code. Once you've pleased with your changes you
can refresh your patch by invoking:

.. code:: bash

    simpy$ hg qrefresh -m 'Description of what this patch does'

Optionally, you may now create another patch on top of the current one by simply
calling:

.. code:: bash

    simpy$ hg qnew my-second-patch

Again, refresh this patch after you are done with your changes.

.. note::

    For more details on Mercurial patch management, see the chapter
    `Managing change with Mercurial Queues
    <http://hgbook.red-bean.com/read/managing-change-with-mercurial-queues.html>`_
    in the Mercurial book.

Submitting patchsets
--------------------

If you are satisfied with your patchset, you can ask Mercurial to create an
email patchbomb and send it to the SimPy development mailinglist.

Configuring email
.................

First, you need to enable the patchbomb extension in Mercurial. Open up
``simpy/.hg/hgrc`` and make sure ``patchbomb`` is listed unter ``extensions``:

::

    [extensions]
    patchbomb =

Next you need to configure your email details. The following settings work for
Google Mail accounts:

::

    [smtp]
    host = smtp.gmail.com
    tls = starttls
    username = <you>@gmail.com

Sending a patchset in a series of emails
........................................

Now you can use Mercurial to send a bunch of emails with patches to the SimPy
development list. For example, if you want to send your currently applied
patchset use the following command:

.. code:: bash

    simpy$ hq email qbase:qtip

.. todo::

    Netiquette stuff about describing a patchset.
