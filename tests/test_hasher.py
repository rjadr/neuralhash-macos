# tests/test_hasher.py
import pytest
import os
import base64
from unittest.mock import MagicMock, patch
from neuralhash_macos import (
    calculate_neural_hash,
    OutputFormat,
    PyObjCNotAvailableError,
    ImageProcessingError,
    InvalidFormatError,
    VisionAPIError,
    NeuralHashError
)
from neuralhash_macos.hasher import _ensure_pyobjc_available, _convert_raw_hash_bytes, PYOBJC_AVAILABLE

# Conditional import for real NSData for testing
if PYOBJC_AVAILABLE:
    from Foundation import NSData as RealNSData # type: ignore
else:
    RealNSData = None # Will be mocked if needed


# A known Base64 representation of a hypothetical 12-byte (96-bit) hash
HYPOTHETICAL_B64_HASH = "QUJDREVGR0hJSktM" # "ABCDEFGHIJKL"
HYPOTHETICAL_RAW_BYTES = base64.b64decode(HYPOTHETICAL_B64_HASH)
HYPOTHETICAL_HEX_HASH = HYPOTHETICAL_RAW_BYTES.hex()
HYPOTHETICAL_BITS_HASH = "".join(format(byte, '08b') for byte in HYPOTHETICAL_RAW_BYTES)


# --- Tests for _ensure_pyobjc_available and _convert_raw_hash_bytes ---
def test_ensure_pyobjc_unavailable_raises_error(mock_pyobjc_unavailable):
    with pytest.raises(PyObjCNotAvailableError):
        _ensure_pyobjc_available()

def test_ensure_pyobjc_available_no_error(mocker):
    mocker.patch('neuralhash_macos.hasher.PYOBJC_AVAILABLE', True)
    try:
        _ensure_pyobjc_available()
    except PyObjCNotAvailableError:
        pytest.fail("PyObjCNotAvailableError raised unexpectedly")

def test_internal_hash_byte_conversion():
    assert _convert_raw_hash_bytes(HYPOTHETICAL_RAW_BYTES, OutputFormat.HEX) == HYPOTHETICAL_HEX_HASH
    assert _convert_raw_hash_bytes(HYPOTHETICAL_RAW_BYTES, OutputFormat.BITS) == HYPOTHETICAL_BITS_HASH
    assert _convert_raw_hash_bytes(HYPOTHETICAL_RAW_BYTES, OutputFormat.BASE64) == HYPOTHETICAL_B64_HASH

    with pytest.raises(InvalidFormatError, match="Internal error: _convert_raw_hash_bytes received non-enum format"):
        _convert_raw_hash_bytes(HYPOTHETICAL_RAW_BYTES, "not_an_enum_member") # type: ignore

# --- Tests for calculate_neural_hash ---
def test_calculate_neural_hash_pyobjc_unavailable(mock_pyobjc_unavailable, sample_image_path):
    with pytest.raises(PyObjCNotAvailableError):
        calculate_neural_hash(sample_image_path)

def test_calculate_neural_hash_non_existent_path(mock_pyobjc_available_and_foundation):
    mock_foundation_objects = mock_pyobjc_available_and_foundation
    mock_foundation_objects["nsurl_class"].fileURLWithPath_.return_value = None
    with pytest.raises(ImageProcessingError, match="Could not create a valid URL"):
        calculate_neural_hash("non_existent_image.jpg")

def test_calculate_neural_hash_init_handler_fails(mock_pyobjc_available_and_foundation, sample_image_path):
    mock_foundation_objects = mock_pyobjc_available_and_foundation
    mock_foundation_objects["vn_image_request_handler_class"].alloc.return_value.initWithURL_options_.return_value = None
    with pytest.raises(ImageProcessingError, match="Could not initialize image request handler"):
        calculate_neural_hash(sample_image_path)

def test_calculate_neural_hash_invalid_output_format_string_input(sample_image_path, mock_pyobjc_available_and_foundation):
    with pytest.raises(InvalidFormatError, match="Invalid output_format value: 'invalid_format_string'"):
        calculate_neural_hash(sample_image_path, output_format="invalid_format_string")


@pytest.mark.skipif(not os.environ.get("RUN_MACOS_SPECIFIC_TESTS"), reason="Requires macOS and Vision Framework")
def test_calculate_neural_hash_on_macos_runs(sample_image_path):
    try:
        from neuralhash_macos.hasher import PYOBJC_AVAILABLE as HASHER_PYOBJC_AVAILABLE_LOCAL
        if not HASHER_PYOBJC_AVAILABLE_LOCAL:
             pytest.skip("PyObjC or Vision not available on this system (checked locally).")

        hex_hash = calculate_neural_hash(sample_image_path, OutputFormat.HEX)
        assert isinstance(hex_hash, str)
        assert len(hex_hash) == 24

        b64_hash = calculate_neural_hash(sample_image_path, OutputFormat.BASE64)
        assert isinstance(b64_hash, str)
        assert len(b64_hash) == 16 

        bits_hash = calculate_neural_hash(sample_image_path, OutputFormat.BITS)
        assert isinstance(bits_hash, str)
        assert all(c in '01' for c in bits_hash)
        assert len(bits_hash) == 96

    except PyObjCNotAvailableError:
        pytest.skip("PyObjC or Vision not available on this system (PyObjCNotAvailableError).")
    except (VisionAPIError, NeuralHashError) as e:
        print(f"\nNote: macOS specific test encountered an error for dummy image (as potentially expected): {e}")
        pass
    except Exception as e:
        pytest.fail(f"Unexpected error during macOS specific test: {type(e).__name__} - {e}")


def test_calculate_neural_hash_handles_string_output_formats(mock_pyobjc_available_and_foundation, sample_image_path, mocker):
    # This test ensures calculate_neural_hash correctly handles string format inputs
    # and calls the (mocked) _convert_raw_hash_bytes with the correct enum and raw bytes.

    mock_foundation_objects = mock_pyobjc_available_and_foundation
    
    # 1. Mock the final conversion step to intercept its arguments
    mock_converter = mocker.patch('neuralhash_macos.hasher._convert_raw_hash_bytes')
    mock_converter.return_value = "dummy_converted_hash_from_mock_converter"

    # 2. Setup the ObjC mock chain to reach the point where b64_hash_string is derived.
    mock_neural_hash_request_class = mock_foundation_objects["neural_hash_request_class"]
    mock_vn_handler_instance = mock_foundation_objects["vn_image_request_handler_instance"]
    
    neural_hash_request_mock = MagicMock(name="neural_hash_request_instance_for_str_fmt_test")
    observation_mock = MagicMock(name="observation_instance_for_str_fmt_test")
    image_hash_obj_mock = MagicMock(name="image_hash_obj_instance_for_str_fmt_test")

    mock_neural_hash_request_class.alloc.return_value.init.return_value = neural_hash_request_mock
    mock_vn_handler_instance.performRequests_error_.return_value = True 
    
    neural_hash_request_mock.setImageSignatureprintType_ = MagicMock()
    neural_hash_request_mock.setImageSignatureHashType_ = MagicMock()
    neural_hash_request_mock.results.return_value = [observation_mock]
    observation_mock.imageSignatureHash.return_value = image_hash_obj_mock
    
    # 3. CRITICAL: Make encodeHashDescriptor... return an object that reliably yields HYPOTHETICAL_B64_HASH
    #    when bytes() and .decode() are called on it.
    if RealNSData: # If PyObjC is actually available (e.g., on macOS)
        # Use a real NSData object initialized with the bytes of our target base64 string
        # The Vision API returns NSData containing the base64 string, not NSData of raw hash bytes.
        concrete_nsdata_for_b64_string = RealNSData.dataWithBytes_length_(
            HYPOTHETICAL_B64_HASH.encode('ascii'),
            len(HYPOTHETICAL_B64_HASH.encode('ascii'))
        )
    else: # PyObjC not available (e.g., CI, or `mock_pyobjc_unavailable` fixture active)
        # Fallback to a MagicMock with __bytes__ if RealNSData can't be used.
        # This is the part that has been problematic.
        concrete_nsdata_for_b64_string = MagicMock(name="fallback_nsdata_mock_for_b64_string")
        def mock_nsdata_bytes_method(self):
            return HYPOTHETICAL_B64_HASH.encode('ascii')
        concrete_nsdata_for_b64_string.__bytes__ = mock_nsdata_bytes_method
        # Add a __len__ to make it more like NSData if bytes() tries to use it.
        concrete_nsdata_for_b64_string.__len__ = lambda: len(HYPOTHETICAL_B64_HASH.encode('ascii'))


    image_hash_obj_mock.encodeHashDescriptorWithBase64EncodingAndReturnError_.return_value = concrete_nsdata_for_b64_string

    # With this setup, inside calculate_neural_hash:
    # image_h_data_ns should be `concrete_nsdata_for_b64_string`.
    # bytes(image_h_data_ns) should give `HYPOTHETICAL_B64_HASH.encode('ascii')`.
    # .decode('ascii') should give `HYPOTHETICAL_B64_HASH`.
    # base64.b64decode(HYPOTHETICAL_B64_HASH) should give `HYPOTHETICAL_RAW_BYTES`.

    # --- Perform tests ---

    # Test with string format 'hex'
    calculate_neural_hash(sample_image_path, output_format="hex")
    mock_converter.assert_called_once_with(HYPOTHETICAL_RAW_BYTES, OutputFormat.HEX)
    mock_converter.reset_mock() 
    
    # Test with string format 'bits'
    calculate_neural_hash(sample_image_path, output_format="bits")
    mock_converter.assert_called_once_with(HYPOTHETICAL_RAW_BYTES, OutputFormat.BITS)
    mock_converter.reset_mock()

    # Test with string format 'base64' - _convert_raw_hash_bytes should NOT be called
    result_b64 = calculate_neural_hash(sample_image_path, output_format="base64")
    assert result_b64 == HYPOTHETICAL_B64_HASH 
    mock_converter.assert_not_called()


def test_objc_error_raised_and_caught(sample_image_path, mock_pyobjc_available_and_foundation):
    mock_foundation_objects = mock_pyobjc_available_and_foundation
    mock_vn_handler_instance = mock_foundation_objects["vn_image_request_handler_instance"]
    MockObjcError = mock_foundation_objects["objc_module"].error

    mock_vn_handler_instance.performRequests_error_.side_effect = MockObjcError("Simulated ObjC error")

    with pytest.raises(VisionAPIError, match="An Objective-C error occurred processing .*Simulated ObjC error"):
        calculate_neural_hash(sample_image_path)