# neuralhash_macos/exceptions.py

class NeuralHashError(Exception):
    """Base exception for neuralhash_macos errors."""
    pass

class PyObjCNotAvailableError(NeuralHashError):
    """Raised when PyObjC or necessary frameworks are not found."""
    pass

class VisionAPIError(NeuralHashError):
    """Raised when there's an error interacting with the Vision API."""
    pass

class ImageProcessingError(NeuralHashError):
    """Raised for errors during image loading or processing."""
    pass

class InvalidFormatError(NeuralHashError):
    """Raised when an invalid output format is requested."""
    pass