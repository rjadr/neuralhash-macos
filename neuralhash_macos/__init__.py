# neuralhash_macos/__init__.py
"""
neuralhash_macos

A Python module to compute NeuralHashes for images on macOS using private Vision APIs.

This tool relies on private, undocumented APIs within Apple's Vision framework.
Its functionality is not guaranteed across different macOS versions and may break
with OS updates. Use at your own risk.
"""

__version__ = "0.1.0"

from .hasher import calculate_neural_hash, OutputFormat
from .exceptions import (
    NeuralHashError,
    PyObjCNotAvailableError,
    VisionAPIError,
    ImageProcessingError,
    InvalidFormatError
)

# Public API
__all__ = [
    "calculate_neural_hash",
    "OutputFormat",
    "NeuralHashError",
    "PyObjCNotAvailableError",
    "VisionAPIError",
    "ImageProcessingError",
    "InvalidFormatError",
    "__version__",
]