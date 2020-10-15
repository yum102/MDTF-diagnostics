"""Define framework-specific exceptions in a single module to simplify imports
for code that has to raise and handle them.
"""
import os
import errno
import logging

_log = logging.getLogger(__name__)

def exit_on_exception(exc, msg=None):
    """Prints information about a fatal exception to the console beofre exiting.
    Use case is in user-facing subcommands (``mdtf install`` etc.), since we 
    have more sophisticated logging in the framework itself.

    Args:
        exc: :py:class:`Exception` object
        msg (str, optional): additional message to print.
    """
    # if subprocess failed, will have already logged its own info
    print('ERROR: caught exception {0}({1!r})'.format(type(exc).__name__, exc.args))
    if msg:
        print(msg)
    exit(1)

class TimeoutAlarm(Exception):
    """Dummy exception raised if a subprocess times out."""
    # NOTE py3 builds timeout into subprocess; fix this
    pass

class MDTFBaseException(Exception):
    """Dummy base class to describe all MDTF-specific errors that can happen
    during the framework's operation."""
    pass

class MDTFFileNotFoundError(FileNotFoundError, MDTFBaseException):
    """Wrapper for :py:class:`FileNotFoundError` which handles error codes so we
    don't have to remember to import :py:mod:`errno` everywhere.
    """
    def __init__(self, path):
        super(MDTFFileNotFoundError, self).__init__(
            errno.ENOENT, os.strerror(errno.ENOENT), path
        )

class MDTFFileExistsError(FileExistsError, MDTFBaseException):
    """Wrapper for :py:class:`FileExistsError` which handles error codes so we
    don't have to remember to import :py:mod:`errno` everywhere.
    """
    def __init__(self, path):
        super(MDTFFileExistsError, self).__init__(
            errno.EEXIST, os.strerror(errno.EEXIST), path
        )

class ConventionError(MDTFBaseException):
    """Exception raised if a subprocess times out."""
    pass

class DataQueryFailure(MDTFBaseException):
    """Exception signaling a failure to find requested data in the remote location. 
    
    Raised by :meth:`~data_manager.DataManager.queryData` to signal failure of a
    data query. Should be caught properly in :meth:`~data_manager.DataManager.planData`
    or :meth:`~data_manager.DataManager.fetchData`.
    """
    def __init__(self, dataset, msg=''):
        self.dataset = dataset
        self.msg = msg

    def __str__(self):
        if hasattr(self.dataset, 'name'):
            return 'Query failure for {}: {}.'.format(self.dataset.name, self.msg)
        else:
            return 'Query failure: {}.'.format(self.msg)

class DataAccessError(MDTFBaseException):
    """Exception signaling a failure to obtain data from the remote location.
    """
    def __init__(self, dataset, msg=''):
        self.dataset = dataset
        self.msg = msg

    def __str__(self):
        if hasattr(self.dataset, '_remote_data'):
            return 'Data access error for {}: {}.'.format(
                self.dataset._remote_data, self.msg)
        else:
            return 'Data access error: {}.'.format(self.msg)

class PodRequirementFailure(MDTFBaseException):
    """Exception raised if POD doesn't have required resources to run, for any
    reason.
    """
    def __init__(self, pod, msg=None):
        self.pod = pod
        self.msg = msg

    def __str__(self):
        if self.msg is not None:
            return ("Requirements not met for {0}."
                "\nReason: {1}.").format(self.pod.name, self.msg)
        else:
            return 'Requirements not met for {}.'.format(self.pod.name)

