# tests/conftest.py
import pytest
import tempfile
import os
from PIL import Image # Requires Pillow: pip install Pillow
import sys # For sys.path modification if needed

# Ensure the package is discoverable if running tests from root
# This might be needed if pytest isn't run with `python -m pytest`
# or if the package isn't installed editable.
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def sample_image_path():
    """Creates a dummy PNG image file and returns its path."""
    img = Image.new('RGB', (1, 1), color = 'black')
    fd, temp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd) # Close the file descriptor before Pillow tries to save
    img.save(temp_path)
    yield temp_path
    os.remove(temp_path)

@pytest.fixture
def mock_pyobjc_unavailable(mocker):
    """Mocks the PYOBJC_AVAILABLE flag in hasher module to be False."""
    return mocker.patch('neuralhash_macos.hasher.PYOBJC_AVAILABLE', False)

@pytest.fixture
def mock_pyobjc_available_and_foundation(mocker):
    """Mocks PYOBJC_AVAILABLE as True and Foundation/Vision components."""
    mocker.patch('neuralhash_macos.hasher.PYOBJC_AVAILABLE', True)

    mock_nsurl_class = mocker.MagicMock()
    mock_nsurl_class.fileURLWithPath_.return_value = mocker.MagicMock(name="NSURLInstance") # Return a mock instance
    mocker.patch('neuralhash_macos.hasher.NSURL', mock_nsurl_class)

    mocker.patch('neuralhash_macos.hasher.NSData', mocker.MagicMock(name="NSDataClass"))
    mocker.patch('neuralhash_macos.hasher.NSLog', mocker.MagicMock(name="NSLogMock"))

    mock_autorelease_pool_class = mocker.MagicMock(name="NSAutoreleasePoolClass")
    mock_autorelease_pool_instance = mocker.MagicMock(name="NSAutoreleasePoolInstance")
    mock_autorelease_pool_class.alloc.return_value.init.return_value = mock_autorelease_pool_instance
    mocker.patch('neuralhash_macos.hasher.NSAutoreleasePool', mock_autorelease_pool_class)

    # Mock Vision framework classes and methods
    mock_vn_image_request_handler_class = mocker.MagicMock(name="VNImageRequestHandlerClass")
    # This is key: the instance returned by initWithURL_options_ needs to be a mock
    mock_vn_image_request_handler_instance = mocker.MagicMock(name="VNImageRequestHandlerInstance")
    mock_vn_image_request_handler_class.alloc.return_value.initWithURL_options_.return_value = mock_vn_image_request_handler_instance
    mocker.patch('neuralhash_macos.hasher.VNImageRequestHandler', mock_vn_image_request_handler_class)

    mock_objc_module = mocker.MagicMock(name="objcModule")
    mock_neural_hash_request_class = mocker.MagicMock(name="NeuralHashRequestClass") # This is the class itself
    mock_objc_module.lookUpClass.return_value = mock_neural_hash_request_class

    # Mock objc.error to be a valid exception type for `except objc.error:`
    # Create a dummy exception class for mocking objc.error
    class MockObjcError(Exception):
        pass
    mock_objc_module.error = MockObjcError

    mocker.patch('neuralhash_macos.hasher.objc', mock_objc_module)


    return {
        "nsurl_class": mock_nsurl_class,
        "vn_image_request_handler_class": mock_vn_image_request_handler_class,
        "vn_image_request_handler_instance": mock_vn_image_request_handler_instance,
        "objc_module": mock_objc_module,
        "neural_hash_request_class": mock_neural_hash_request_class,
        "autorelease_pool_instance": mock_autorelease_pool_instance,
    }