import logging

_log = logging.getLogger(__name__)

class TimeoutAlarm(Exception):
    """Dummy exception raised if a subprocess times out."""
    # NOTE py3 builds timeout into subprocess; fix this
    pass

class MDTFException(Exception):
    """Dummy base class to describe all MDTF-specific errors that can happen
    during the framework's operation."""
    pass

class ConventionError(MDTFException):
    """Exception raised if a subprocess times out."""
    pass

class DataQueryFailure(MDTFException):
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

class DataAccessError(MDTFException):
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

class PodRequirementFailure(MDTFException):
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

