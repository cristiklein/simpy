"""
Exceptions used by SimPy.

"""
import traceback
import sys


class Interrupt(Exception):
    """This exceptions is sent into a process if it was interrupted by
    another process.

    """
    def __init__(self, cause):
        super(Interrupt, self).__init__(cause)

    @property
    def cause(self):
        return self.args[0]


class Failure(Exception):
    """This exception indicates that a process failed during its execution."""
    if sys.version_info < (3, 0):
        # Exception chaining was added in Python 3. Mimic exception chaining as
        # good as possible for Python 2.
        def __init__(self):
            super(Failure, self).__init__()
            self.stacktrace = traceback.format_exc(sys.exc_info()[2]).strip()

        def __str__(self):
            return 'Caused by the following exception:\n\n%s' % (
                    self.stacktrace)

    def __str__(self):
        return '%s' % self.__cause__


class SimEnd(Exception):
    """This exception is raised by :meth:`simpy.Simulation.step` if
    there are no more events in the event quque.

    """
