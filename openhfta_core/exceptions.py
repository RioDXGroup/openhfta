class OpenHFTAError(Exception):
    """Base class for domain errors raised by the reusable library."""

class ValidationError(OpenHFTAError, ValueError):
    pass

class ProfileError(ValidationError):
    pass

class LibraryError(OpenHFTAError, RuntimeError):
    pass

class AnalysisError(OpenHFTAError, RuntimeError):
    pass
