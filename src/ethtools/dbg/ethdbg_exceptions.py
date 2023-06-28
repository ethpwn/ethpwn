
class InvalidBreakpointException(Exception):
    pass

class ExitCmdException(Exception):
    pass

class RestartDbgException(Exception):
    pass

class InvalidTargetException(Exception):
    def __init__(self, target_address):
        self.target_address = target_address
    pass