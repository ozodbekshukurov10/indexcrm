class ServiceError(Exception):
    default_message = "A service error occurred."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)
