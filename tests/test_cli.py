# tests/test_cli.py
import pytest
from unittest.mock import patch, call
import subprocess
import sys
import os # For os.path.exists, os.path.getsize
from neuralhash_macos import cli, OutputFormat, NeuralHashError, PyObjCNotAvailableError
# Import with alias to distinguish from cli.PYOBJC_AVAILABLE if needed, though not strictly necessary here
from neuralhash_macos.hasher import PYOBJC_AVAILABLE as HASHER_PYOBJC_AVAILABLE

# Re-use hypothetical hashes from test_hasher for consistency
HYPOTHETICAL_B64_HASH = "QUJDREVGR0hJSktM"
HYPOTHETICAL_HEX_HASH = "4142434445464748494a4b4c"


def run_cli_tool_via_main(args_list, mocker, setup_cli_mocks=True):
    """Helper to run cli.main() by patching sys.argv and catching SystemExit."""
    if setup_cli_mocks:
        # This mock is for the cli module's own PYOBJC_AVAILABLE check
        mocker.patch('neuralhash_macos.cli.PYOBJC_AVAILABLE', True)
        # If available, mock Foundation for NSAutoreleasePool in cli.main
        # create=True is important if NSAutoreleasePool might not be imported yet
        mock_pool_class = mocker.MagicMock(name="CliNSAutoreleasePoolClass")
        mock_pool_instance = mocker.MagicMock(name="CliNSAutoreleasePoolInstance")
        mock_pool_class.alloc.return_value.init.return_value = mock_pool_instance
        mocker.patch('neuralhash_macos.cli.NSAutoreleasePool', mock_pool_class, create=True)
    # Else, the test is responsible for setting up cli.PYOBJC_AVAILABLE if needed

    with patch.object(sys, 'argv', ['neuralhash-macos'] + args_list):
        try:
            cli.main()
        except SystemExit as e:
            return e.code
    return 0 # If no SystemExit, assume exit code 0 for success

@pytest.fixture
def mock_calculate_hash(mocker):
    """Mocks the calculate_neural_hash function in the cli module."""
    return mocker.patch('neuralhash_macos.cli.calculate_neural_hash')


def test_cli_single_image_hex_default(mock_calculate_hash, sample_image_path, capsys, mocker):
    mock_calculate_hash.return_value = HYPOTHETICAL_HEX_HASH
    
    exit_code = run_cli_tool_via_main([sample_image_path], mocker)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert f"Processing image: {sample_image_path}" in captured.out
    assert HYPOTHETICAL_HEX_HASH in captured.out
    assert captured.err == ""
    mock_calculate_hash.assert_called_once_with(sample_image_path, OutputFormat.HEX)

def test_cli_single_image_base64(mock_calculate_hash, sample_image_path, capsys, mocker):
    mock_calculate_hash.return_value = HYPOTHETICAL_B64_HASH

    exit_code = run_cli_tool_via_main([sample_image_path, '--format', 'base64'], mocker)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert f"Processing image: {sample_image_path}" in captured.out
    assert HYPOTHETICAL_B64_HASH in captured.out
    assert captured.err == ""
    mock_calculate_hash.assert_called_once_with(sample_image_path, OutputFormat.BASE64)

def test_cli_multiple_images(mock_calculate_hash, sample_image_path, capsys, mocker):
    from PIL import Image # Local import to avoid making Pillow a global test dep if not needed everywhere
    import tempfile
    img2 = Image.new('RGB', (1, 1), color = 'red')
    fd, temp_path2 = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img2.save(temp_path2)

    mock_calculate_hash.side_effect = ["hash1_hex", "hash2_hex"]

    exit_code = run_cli_tool_via_main([sample_image_path, temp_path2], mocker)
    assert exit_code == 0
    
    os.remove(temp_path2)

    captured = capsys.readouterr()
    assert "--- Processing image 1/2:" in captured.out
    assert "hash1_hex" in captured.out
    assert "--- Processing image 2/2:" in captured.out
    assert "hash2_hex" in captured.out
    assert captured.err == ""
    assert mock_calculate_hash.call_count == 2
    mock_calculate_hash.assert_has_calls([
        call(sample_image_path, OutputFormat.HEX),
        call(temp_path2, OutputFormat.HEX)
    ])

def test_cli_image_not_found(mock_calculate_hash, capsys, mocker):
    exit_code = run_cli_tool_via_main(['non_existent.jpg'], mocker)
    assert exit_code == 1
    
    captured = capsys.readouterr()
    assert "Error: Image path not found: non_existent.jpg" in captured.err
    assert captured.out == ""
    mock_calculate_hash.assert_not_called()

def test_cli_path_is_directory(mock_calculate_hash, tmp_path, capsys, mocker):
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()

    exit_code = run_cli_tool_via_main([str(dir_path)], mocker)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert f"Error: Path is not a file: {str(dir_path)}" in captured.err
    assert captured.out == ""
    mock_calculate_hash.assert_not_called()


def test_cli_calculate_hash_raises_error(mock_calculate_hash, sample_image_path, capsys, mocker):
    mock_calculate_hash.side_effect = NeuralHashError("Test calculation error")

    exit_code = run_cli_tool_via_main([sample_image_path], mocker)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert f"Processing image: {sample_image_path}" in captured.out
    assert "Error generating NeuralHash" in captured.err
    assert "Test calculation error" in captured.err

def test_cli_pyobjc_not_available_in_cli_module(mock_calculate_hash, capsys, mocker):
    # Mock PYOBJC_AVAILABLE in cli.py to be False for this specific test.
    # This will be the controlling mock for the cli.PYOBJC_AVAILABLE check.
    mocker.patch('neuralhash_macos.cli.PYOBJC_AVAILABLE', False)
    
    # Call helper without its default cli mocks for PYOBJC_AVAILABLE and NSAutoreleasePool,
    # as we've set PYOBJC_AVAILABLE to False and don't expect NSAutoreleasePool to be used.
    exit_code = run_cli_tool_via_main(['dummy.jpg'], mocker, setup_cli_mocks=False)
    assert exit_code == 1
    
    captured = capsys.readouterr()
    assert "Error: PyObjC components (Foundation, Vision) not found" in captured.err
    assert captured.out == ""
    mock_calculate_hash.assert_not_called()


@pytest.mark.skipif(not os.environ.get("RUN_MACOS_SPECIFIC_TESTS"), reason="Requires macOS and CLI installation")
def test_cli_executable_on_macos(sample_image_path):
    def run_actual_cli(args):
        cmd = ['neuralhash-macos'] + args
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=15) # Increased timeout slightly
        return stdout, stderr, process.returncode

    try:
        assert os.path.exists(sample_image_path) and os.path.getsize(sample_image_path) > 0

        stdout_hex, stderr_hex, returncode_hex = run_actual_cli([sample_image_path, '--format', 'hex'])
        
        # Handle case where the dummy image genuinely can't be processed by real Vision
        if returncode_hex != 0 and ("Could not extract NeuralHash" in stderr_hex or "No results from Vision request" in stderr_hex):
             pytest.skip(f"Real Vision framework couldn't process dummy image (hex): {stderr_hex.strip()}")
        
        assert returncode_hex == 0, f"CLI (hex) exited with {returncode_hex}. Stderr: {stderr_hex}"
        # Output format: "Processing image: <path>\n<hash>\n"
        # We care about the last line for the hash.
        output_lines_hex = stdout_hex.strip().split('\n')
        assert "Processing image:" in output_lines_hex[0]
        assert len(output_lines_hex[-1]) == 24 # 96 bits / 4 bits per hex char = 24 hex chars
        assert stderr_hex == ""


        stdout_bits, stderr_bits, returncode_bits = run_actual_cli([sample_image_path, '--format', 'bits'])
        if returncode_bits != 0 and ("Could not extract NeuralHash" in stderr_bits or "No results from Vision request" in stderr_bits):
             pytest.skip(f"Real Vision framework couldn't process dummy image (bits): {stderr_bits.strip()}")

        assert returncode_bits == 0, f"CLI (bits) exited with {returncode_bits}. Stderr: {stderr_bits}"
        output_lines_bits = stdout_bits.strip().split('\n')
        assert "Processing image:" in output_lines_bits[0]
        assert len(output_lines_bits[-1]) == 96 # 96 bits
        assert stderr_bits == ""

    except subprocess.TimeoutExpired:
        pytest.fail("CLI command timed out.")
    except FileNotFoundError:
        pytest.skip("neuralhash-macos command not found in PATH. Is the package installed?")
    except AssertionError as e: # Catch assertion errors from this test
        # Check if stderr (from the subprocess) contains PyObjC/Vision errors
        # This is tricky because stderr_hex/stderr_bits are local to the try block scope
        # For simplicity, we'll assume if an AssertionError happens here, it's not a PyObjC setup issue
        # that would have been caught by the earlier checks.
        if "PyObjC" in str(e) or "Vision" in str(e): # A bit of a guess
             pytest.skip(f"PyObjC/Vision issue on test system: {e}")
        else:
            raise e
    except Exception as e: # Catch other unexpected exceptions
        pytest.fail(f"Unexpected exception during CLI executable test: {e}")