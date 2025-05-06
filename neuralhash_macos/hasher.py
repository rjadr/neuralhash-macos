# neuralhash_macos/hasher.py
"""
Core module for calculating NeuralHashes on macOS using the Vision framework.

This module relies on private, obfuscated APIs within Apple's Vision framework.
Its functionality is not guaranteed across different macOS versions and may
break with OS updates.
"""

import base64
import logging
import sys
from enum import Enum
import objc # PyObjC's core module

from .exceptions import (
    NeuralHashError,
    PyObjCNotAvailableError,
    VisionAPIError,
    ImageProcessingError,
    InvalidFormatError
)

# Standard library logger
logger = logging.getLogger(__name__)

# Attempt to import PyObjC modules and set a flag
try:
    from Foundation import NSURL, NSData, NSAutoreleasePool, NSLog # type: ignore
    from Vision import VNImageRequestHandler # type: ignore
    PYOBJC_AVAILABLE = True
except ImportError:
    PYOBJC_AVAILABLE = False
    # Define dummy classes/objects if not available to allow module import
    NSURL, NSData, NSAutoreleasePool, VNImageRequestHandler = (None,) * 4
    # Fallback for NSLog if Foundation is not available
    def NSLog(msg_format, *args): # pragma: no cover
        """Fallback NSLog for when Foundation is not available."""
        # pylint: disable=unused-argument
        logger.warning(
            "NSLog (fallback): %s",
            msg_format % args if args else msg_format
        )

# Obfuscated class names from Apple's private Vision API
OBFUSCATED_REQUEST_CLASS_NAME = "VN6kBnCOr2mZlSV6yV1dLwB"

class OutputFormat(Enum):
    """Enum for specifying the desired output format of the NeuralHash."""
    HEX = "hex"
    BASE64 = "base64"
    BITS = "bits"

def _ensure_pyobjc_available():
    """Checks if PyObjC and necessary frameworks are available."""
    if not PYOBJC_AVAILABLE:
        raise PyObjCNotAvailableError(
            "PyObjC (Foundation, Vision) not found or not properly installed. "
            "Please install it, e.g., "
            "'pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Vision'"
        )

def _convert_raw_hash_bytes(
    raw_bytes: bytes,
    output_format_enum: OutputFormat # Expecting an enum member here
) -> str:
    """
    Converts raw hash bytes to the specified string format.
    Assumes raw_bytes is the actual perceptual hash, not a base64 encoding of it.
    """
    if not isinstance(output_format_enum, OutputFormat):
        # This function expects an enum, caller should handle string-to-enum conversion.
        # If it receives something else, it's an internal logic error.
        raise InvalidFormatError(
             f"Internal error: _convert_raw_hash_bytes received non-enum format: {output_format_enum}"
        )

    if output_format_enum == OutputFormat.HEX:
        return raw_bytes.hex()
    if output_format_enum == OutputFormat.BITS:
        return "".join(format(byte, '08b') for byte in raw_bytes)
    if output_format_enum == OutputFormat.BASE64:
        logger.warning("_convert_raw_hash_bytes called with raw bytes and BASE64 format. This is unusual.")
        return base64.b64encode(raw_bytes).decode('ascii')
    
    # This part should ideally not be reached if OutputFormat enum is exhaustive
    # and input is validated to be an OutputFormat member.
    # However, to be safe for future enum changes:
    raise InvalidFormatError(f"Unsupported output format for raw byte conversion: {output_format_enum.value}")


def calculate_neural_hash(
    image_path: str,
    output_format: OutputFormat = OutputFormat.HEX # Accept string or Enum
) -> str:
    _ensure_pyobjc_available()

    output_format_enum: OutputFormat
    if isinstance(output_format, OutputFormat):
        output_format_enum = output_format
    else:
        try:
            output_format_enum = OutputFormat(str(output_format).lower())
        except ValueError:
            raise InvalidFormatError(
                f"Invalid output_format value: '{output_format}'. "
                f"Must be one of {[fmt.value for fmt in OutputFormat]} or an OutputFormat enum member."
            ) from None

    pool = NSAutoreleasePool.alloc().init()
    try:
        try:
            NeuralHashRequestClass = objc.lookUpClass(OBFUSCATED_REQUEST_CLASS_NAME)
        except objc.NotFoundError:
            msg = f"Required Vision class '{OBFUSCATED_REQUEST_CLASS_NAME}' not found."
            NSLog("Python NeuralHash: Class '%@' not found.", OBFUSCATED_REQUEST_CLASS_NAME)
            raise VisionAPIError(msg)

        image_url = NSURL.fileURLWithPath_(image_path)
        if image_url is None:
            msg = f"Could not create a valid URL for path '{image_path}'."
            NSLog("Python NeuralHash: Could not create NSURL for path: %@", image_path)
            raise ImageProcessingError(msg)

        request_handler = VNImageRequestHandler.alloc().initWithURL_options_(image_url, None)
        if request_handler is None:
            msg = f"Could not initialize image request handler for '{image_path}'."
            NSLog("Python NeuralHash: Failed to init VNImageRequestHandler for path: %@", image_path)
            raise ImageProcessingError(msg)

        neural_hash_request = NeuralHashRequestClass.alloc().init()
        if neural_hash_request is None:
            msg = f"Failed to init NeuralHash request object ('{OBFUSCATED_REQUEST_CLASS_NAME}')."
            NSLog("Python NeuralHash: Failed to init %@", OBFUSCATED_REQUEST_CLASS_NAME)
            raise VisionAPIError(msg)

        if not hasattr(neural_hash_request, 'setImageSignatureprintType_') or \
           not hasattr(neural_hash_request, 'setImageSignatureHashType_'):
            msg = (f"{OBFUSCATED_REQUEST_CLASS_NAME} instance missing required setters. "
                   "API mismatch or PyObjC bridging issue.")
            NSLog("Python NeuralHash: %@ missing required setters.", OBFUSCATED_REQUEST_CLASS_NAME)
            raise VisionAPIError(msg)

        neural_hash_request.setImageSignatureprintType_(3)
        neural_hash_request.setImageSignatureHashType_(1)

        success = request_handler.performRequests_error_([neural_hash_request], None)
        if not success:
            msg = (f"Vision request failed for '{image_path}' "
                   "(performRequests returned False without raising an exception).")
            NSLog("Python NeuralHash: performRequests_error_ returned False for %@.", image_path)
            raise VisionAPIError(msg)

        results = neural_hash_request.results()
        if not results:
            msg = f"No results returned from Vision request for '{image_path}'."
            NSLog("Python NeuralHash: No results from Vision request for %@.", image_path)
            raise VisionAPIError(msg)

        for observation in results:
            if not hasattr(observation, 'imageSignatureHash'):
                actual_class_name = "Unknown"
                try: actual_class_name = observation.className()
                except: pass
                logger.warning("Python NeuralHash: Observation (class: %s) does not have 'imageSignatureHash' method for %s.", actual_class_name, image_path)
                continue

            image_hash_obj = observation.imageSignatureHash()
            if image_hash_obj is None:
                logger.warning("Python NeuralHash: imageSignatureHash() returned None for %s.", image_path)
                continue

            if not hasattr(image_hash_obj, 'encodeHashDescriptorWithBase64EncodingAndReturnError_'):
                actual_class_name = "Unknown"
                try: actual_class_name = image_hash_obj.className()
                except: pass
                msg = (f"Hash object for '{image_path}' (class: {actual_class_name}) "
                       "does not support the required encoding method.")
                NSLog("Python NeuralHash: image_hash_object (class: %@) does not have 'encodeHashDescriptorWithBase64EncodingAndReturnError_' method.", actual_class_name)
                raise VisionAPIError(msg)
            
            image_h_data_ns = image_hash_obj.encodeHashDescriptorWithBase64EncodingAndReturnError_(None)
            if image_h_data_ns is None:
                msg = (f"Encoding hash descriptor for '{image_path}' failed "
                       "(encodeHashDescriptor... returned None).")
                NSLog("Python NeuralHash: encodeHashDescriptorWithBase64Encoding returned None for %@.", image_path)
                raise VisionAPIError(msg)
                
            b64_encoded_hash_bytes = bytes(image_h_data_ns)
            b64_hash_string = b64_encoded_hash_bytes.decode('ascii')
            
            if not b64_hash_string and output_format_enum != OutputFormat.BASE64: # If empty b64 and not asking for b64
                logger.warning("Python NeuralHash: Obtained empty base64 string for %s. Cannot derive other formats.", image_path)
                # Depending on strictness, either continue or raise. Let's be strict.
                raise NeuralHashError(f"Obtained empty base64 hash string for '{image_path}'. Cannot derive HEX or BITS.")


            if output_format_enum == OutputFormat.BASE64:
                return b64_hash_string

            try:
                raw_hash_bytes = base64.b64decode(b64_hash_string)
            except base64.binascii.Error as exc:
                msg = f"Failed to decode base64 hash string ('{b64_hash_string}') for '{image_path}': {exc}"
                NSLog("Python NeuralHash: Base64 decoding error for %@: %@",
                      image_path, b64_hash_string)
                raise NeuralHashError(msg) from exc
            
            return _convert_raw_hash_bytes(raw_hash_bytes, output_format_enum)

        msg = f"Could not extract NeuralHash from any observation for '{image_path}'."
        NSLog("Python NeuralHash: Failed to extract hash from any observation for %@.", image_path)
        raise NeuralHashError(msg)

    except objc.error as exc:
        msg = f"An Objective-C error occurred processing {image_path}: {exc}"
        NSLog(f"Python NeuralHash: An Objective-C error occurred processing {image_path}: {exc}")
        raise VisionAPIError(msg) from exc
    except AttributeError as exc:
        NSLog(f"Python NeuralHash: An AttributeError occurred processing {image_path}: {exc}")
        raise VisionAPIError(f"An AttributeError occurred: {exc}. API mismatch or PyObjC issue.") from exc
    except (ImageProcessingError, VisionAPIError, InvalidFormatError, NeuralHashError):
        raise
    except Exception as exc:
        NSLog(f"Python NeuralHash: A Python error occurred processing {image_path}: {type(exc).__name__} - {exc}")
        raise NeuralHashError(f"A Python error occurred while processing '{image_path}': {type(exc).__name__} - {exc}") from exc
    finally:
        if PYOBJC_AVAILABLE and 'pool' in locals() and pool is not None:
            del pool # type: ignore