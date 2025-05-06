# NeuralHash macOS

A Python module and command-line tool to compute Apple's NeuralHash for local image files on macOS. This tool leverages private, undocumented APIs within Apple's Vision framework.

**⚠️ Important Disclaimer:** This software interacts with private Apple APIs. Its functionality is not guaranteed, may change or break with any macOS update, and should not be relied upon for critical applications. Use at your own risk. This tool is intended for research and educational purposes.

Based on the original research and proof-of-concept by [KhaosT (nhcalc)](https://github.com/KhaosT/nhcalc).

## Features

*   Calculate NeuralHash for image files.
*   Output hash in multiple formats:
    *   `hex` (default): Hexadecimal representation of the raw hash bytes.
    *   `base64`: Base64 encoded string of the raw hash bytes.
    *   `bits`: Binary string representation of the raw hash bytes.
*   Usable as a Python library or a command-line tool.

## Requirements

*   **macOS**: This tool uses macOS-specific frameworks (Vision).
*   **Python**: 3.8 or newer.
*   **PyObjC**: Python bindings for Objective-C frameworks. Specifically:
    *   `pyobjc-core`
    *   `pyobjc-framework-Cocoa`
    *   `pyobjc-framework-Vision`

## Installation

### 1. Install PyObjC (Prerequisite)

It's often best to install PyObjC using pip. Depending on your macOS version and Python setup, you might need to ensure Xcode Command Line Tools are installed.

```bash
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Vision
```
*Note: PyObjC version compatibility can sometimes be an issue. The `pyproject.toml` specifies versions `>=9.0`, which are generally compatible with recent macOS versions. If you encounter issues, you may need to experiment with different PyObjC versions.*

### 2. Install NeuralHash macOS

You have a few options to install this module:

#### Option A: Install directly from GitHub (Recommended for latest version)

You can install the latest version directly from the `main` branch on GitHub using `pip`:

```bash
pip install git+https://github.com/rjadr/neuralhash-macos.git
```

#### Option B: Install from a local clone (For development or specific versions)

Clone the repository and install using `pip`:

```bash
git clone https://github.com/rjadr/neuralhash-macos.git # Replace with your repo URL
cd neuralhash-macos
pip install .
```

For development, you can install it in editable mode:
```bash
pip install -e .
```
This allows you to make changes to the code and have them immediately reflected without reinstalling. If you plan to contribute or modify the code, this is the recommended method after cloning.

## Usage

### As a Command-Line Tool

The installer adds `neuralhash-macos` to your PATH.

```bash
neuralhash-macos [OPTIONS] PATH_TO_IMAGE [PATH_TO_IMAGE_2 ...]
```

**Options:**

*   `PATH_TO_IMAGE`: One or more paths to image files.
*   `--format FORMAT`, `-f FORMAT`: Output format. Choices: `hex`, `base64`, `bits`. Default: `hex`.
*   `--verbose`, `-v`: Enable verbose output.
*   `--debug`: Enable debug output (includes internal logging).
*   `--help`: Show help message.

**Examples:**

*   Get hex hash for a single image:
    ```bash
    neuralhash-macos my_image.jpg
    ```
    Output:
    ```
    Processing image: my_image.jpg
    d8943808fa8ef1082408088000c0400000080000000000000000 # Example hash
    ```

*   Get base64 hash for multiple images:
    ```bash
    neuralhash-macos -f base64 image1.png image2.jpeg
    ```
    Output:
    ```
    --- Processing image 1/2: image1.png ---
    2JQ4CPqO8QgkBACAgMBBAAAIAAAAAAAA
    ------------------------------
    --- Processing image 2/2: image2.jpeg ---
    anotherBase64HashExampleString==
    ```

*   Get bits hash:
    ```bash
    neuralhash-macos --format bits photo.heic
    ```

### As a Python Library

```python
from neuralhash_macos import calculate_neural_hash, OutputFormat, NeuralHashError

try:
    # Get hash in default hex format
    hex_hash = calculate_neural_hash("path/to/your/image.jpg")
    print(f"Hex Hash: {hex_hash}")

    # Get hash in base64 format
    b64_hash = calculate_neural_hash("path/to/another/image.png", OutputFormat.BASE64)
    print(f"Base64 Hash: {b64_hash}")

    # Get hash in bits format
    bits_hash = calculate_neural_hash("path/to/image.heic", OutputFormat.BITS)
    print(f"Bits Hash: {bits_hash}")

except NeuralHashError as e:
    print(f"An error occurred: {e}")
except FileNotFoundError:
    print("Error: Image file not found.")
except Exception as e:
    print(f"An unexpected error: {e}")

```

## How it Works (Briefly)

The script uses PyObjC to interact with Apple's private Vision framework. It specifically looks up an obfuscated class (identified as `VN6kBnCOr2mZlSV6yV1dLwB`) and uses its methods to request an "image signature print" which is believed to be the NeuralHash. The raw hash (typically 96 bits or 12 bytes) is then encoded into the requested format (hex, base64, or bits).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

*   [KhaosT](https://github.com/KhaosT) for the original `nhcalc` project and discovery of the method.