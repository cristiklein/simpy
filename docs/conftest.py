# coding=utf-8
"""
This module scans all ``*.rst`` files below ``docs/`` for example code. Example
code is discoved by checking for lines containing the ``.. literalinclude:: ``
directives.

An example consists of two consecutive literalinclude directives. The first
must include a ``*.py`` file and the second a ``*.out`` file. The ``*.py`` file
consists of the example code which is executed in a separate process. The
output of this process is compared to the contents of the ``*.out`` file.

"""
import os.path
import subprocess
import errno
import random

import pytest
from py._code.code import TerminalRepr
from _pytest.assertion.util import _diff_text


blacklist = ['SimRTManual.rst']
"""A list of strings with rst-files to skip."""


def pytest_collect_file(path, parent):
    """Checks if the file is a rst file and creates an :class:`ExampleFile`
    instance."""
    if path.ext != '.rst':
        return
    for item in blacklist:
        if str(path).endswith(item):
            return
    return ExampleFile(path, parent)


class ExampleFile(pytest.File):
    """Collects all examples contained in a rst-file."""

    def collect(self):
        # Collect all literal includes.
        literalincludes = []
        with self.fspath.open() as data:
            for lineno, line in enumerate(data):
                if 'literalinclude' not in line:
                    continue
                filename = line.split('::')[-1].strip()
                filepath = os.path.join(self.fspath.dirname, filename)
                literalincludes.append((lineno, filepath))

        # Check for directly following output specification.
        for idx in range(len(literalincludes) - 1):
            example_lineno, example = literalincludes[idx]
            output_lineno, output = literalincludes[idx + 1]
            if not example.endswith('.py'):
                continue
            if not output.endswith('.out'):
                continue
            yield ExampleItem(output_lineno, example, output, self)


class ExampleItem(pytest.Item):
    """Executes an example found in a rst-file."""

    def __init__(self, lineno, example, output, parent):
        pytest.Item.__init__(self, example, parent)
        self.lineno = lineno
        self.example = example
        self.output = output
        self.examplefile = os.path.join(self.fspath.dirname, self.example)
        self.outputfile = os.path.join(self.fspath.dirname, self.output)

    def runtest(self):
        # Skip if random.expovariate with the old implementation is used.
        with open(self.examplefile) as f:
            src = f.read()
        if 'expovariate' in src:
            random.seed(0)
            if int(random.expovariate(0.2)) == 0:
                pytest.skip('Old exovariate implementation.')

        # Read expected output.
        with open(self.outputfile) as f:
            expected = f.read()

        # Execute the example.
        if not hasattr(subprocess, 'check_output'):  # The case on Python 2.6
            pytest.skip('subprocess has no check_output() method.')

        output = subprocess.check_output(['python', self.examplefile],
                stderr=subprocess.STDOUT)

        if isinstance(output, bytes):  # The case on Python 3
            output = output.decode('utf8')

        if output != expected:
            # Hijack the ValueError exception to identify mismatching output.
            raise ValueError(expected, output)

    def repr_failure(self, exc_info):
        if exc_info.errisinstance((ValueError,)):
            # Output is mismatching. Create a nice diff as failure description.
            expected, output = exc_info.value.args

            message = _diff_text(expected, output)
            return ReprFailExample(self.fspath.basename, self.lineno,
                    self.outputfile, message)
        elif exc_info.errisinstance((IOError,)):
            # Something wrent wrong causing an IOError.
            if exc_info.value.errno != errno.ENOENT:
                # This isn't a file not found error so bail out and report the
                # error in detail.
                return pytest.Item.repr_failure(self, exc_info)
            # Otherwise provide a concise error description.
            return ReprFileNotFoundExample(self.fspath.basename, self.lineno,
                    self.examplefile, exc_info)
        elif exc_info.errisinstance((subprocess.CalledProcessError,)):
            # Something wrent wrong while executing the example. Provide a
            # concise error description.
            return ReprErrorExample(self.fspath.basename, self.lineno,
                    self.examplefile, exc_info)
        else:
            # Something went terribly wrong :(
            return pytest.Item.repr_failure(self, exc_info)

    def reportinfo(self):
        """Returns a description of the example."""
        return self.fspath, None, '[example %s]' % (
                os.path.relpath(self.examplefile))


class ReprFailExample(TerminalRepr):
    """Reports output mismatches in a nice and informative representation."""

    Markup = {
            '+': dict(green=True),
            '-': dict(red=True),
            '?': dict(bold=True),
    }
    """Colorize codes for the diff markup."""

    def __init__(self, filename, lineno, outputfile, message):
        self.filename = filename
        self.lineno = lineno
        self.outputfile = outputfile
        self.message = message

    def toterminal(self, tw):
        for line in self.message:
            markup = ReprFailExample.Markup.get(line[0], {})
            tw.line(line, **markup)
        tw.line('%s:%d (in %s): Unexpected output' % (self.filename,
                self.lineno, os.path.relpath(self.outputfile)))


class ReprErrorExample(TerminalRepr):
    """Reports failures in the execution of an example."""

    def __init__(self, filename, lineno, examplefile, exc_info):
        self.filename = filename
        self.lineno = lineno
        self.examplefile = examplefile
        self.exc_info = exc_info

    def toterminal(self, tw):
        tw.line('Execution failed! Captured output:', bold=True)
        tw.sep('-')
        tw.line(self.exc_info.value.output, red=True, bold=True)
        tw.line('%s:%d (%s) Example failed (exitcode=%d)' % (self.filename,
                self.lineno, os.path.relpath(self.examplefile),
                self.exc_info.value.returncode))


class ReprFileNotFoundExample(TerminalRepr):
    """Reports concise error information in the case of a file not found."""

    def __init__(self, filename, lineno, examplefile, exc_info):
        self.filename = filename
        self.lineno = lineno
        self.examplefile = examplefile
        self.exc_info = exc_info

    def toterminal(self, tw):
        tw.line(self.exc_info.value, red=True, bold=True)
        tw.line('%s:%d (%s) Example failed' % (self.filename,
                self.lineno, os.path.relpath(self.examplefile)))
