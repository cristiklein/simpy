"""
Compatibility helpers for older Python versions.

"""
import sys


PY2 = sys.version_info[0] == 2


if PY2:
    # Python 2.x does not report exception chains. To emulate the behaviour of
    # Python 3 the functions format_chain and print_chain are added. The latter
    # function is used to override the exception hook of Python 2.x.
    from traceback import format_exception

    def format_chain(exc_type, exc_value, exc_traceback):
        if hasattr(exc_value, '__cause__') and exc_value.__cause__:
            cause = exc_value.__cause__
            if hasattr(exc_value, '__traceback__'):
                traceback = exc_value.__traceback__
            else:
                traceback = None
            lines = format_chain(type(cause), cause, traceback)
            lines += ('\nThe above exception was the direct cause of the '
                      'following exception:\n\n')
        else:
            lines = []

        return lines + format_exception(exc_type, exc_value, exc_traceback)

    def print_chain(exc_type, exc_value, exc_traceback):
        sys.stderr.write(''.join(format_chain(exc_type, exc_value,
                                              exc_traceback)))
        sys.stderr.flush()

    sys.excepthook = print_chain
