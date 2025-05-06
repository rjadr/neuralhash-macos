# neuralhash_macos/cli.py
"""
Command-line interface for the neuralhash_macos module.
"""

import argparse
import sys
import logging
import os

from neuralhash_macos import (
    calculate_neural_hash,
    OutputFormat,
    NeuralHashError,
    PyObjCNotAvailableError
)
from neuralhash_macos.hasher import PYOBJC_AVAILABLE

# Setup basic logging for the CLI
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main function for the CLI."""
    if PYOBJC_AVAILABLE:
        # PyObjC requires an autorelease pool for its operations.
        # Import Foundation here, as it might not be available if PYOBJC_AVAILABLE is False.
        from Foundation import NSAutoreleasePool
        pool = NSAutoreleasePool.alloc().init()
    else:
        pool = None # To satisfy pylint, though it won't be used

    parser = argparse.ArgumentParser(
        description=(
            "Compute NeuralHash for image(s) using macOS Vision framework. "
            "Relies on private Apple APIs; may break with OS updates."
        ),
        epilog=(
            "Example: neuralhash-macos path/to/image.jpg --format hex\n"
            "Note: Requires PyObjC (see README for installation)."
        )
    )
    parser.add_argument(
        "image_paths",
        metavar="PATH_TO_IMAGE",
        type=str,
        nargs='+',
        help="Path(s) to the image file(s) to process."
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=[fmt.value for fmt in OutputFormat],
        default=OutputFormat.HEX.value,
        help=(
            "Output format for the hash. "
            f"Options: {', '.join([fmt.value for fmt in OutputFormat])}. "
            f"Default: {OutputFormat.HEX.value}."
        )
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (INFO level logging)."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (DEBUG level logging, including NSLog via Python logger)."
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger('neuralhash_macos').setLevel(logging.INFO)
    if args.debug:
        logging.getLogger('neuralhash_macos').setLevel(logging.DEBUG)
        # Also configure the root logger for PyObjC's NSLog messages if they are redirected
        # or for general debug messages from other libraries if needed.
        logging.basicConfig(level=logging.DEBUG)


    if not PYOBJC_AVAILABLE:
        # This check is also in hasher.py, but good to have early exit in CLI
        print(
            "Error: PyObjC components (Foundation, Vision) not found. "
            "This tool cannot function on this system or without these libraries.",
            file=sys.stderr
        )
        print("Please see installation instructions in README.md.", file=sys.stderr)
        sys.exit(1)


    any_successful_processing = False
    exit_code = 0

    for i, image_path in enumerate(args.image_paths):
        if not os.path.exists(image_path):
            print(f"Error: Image path not found: {image_path}", file=sys.stderr)
            exit_code = 1
            continue
        if not os.path.isfile(image_path):
            print(f"Error: Path is not a file: {image_path}", file=sys.stderr)
            exit_code = 1
            continue

        if len(args.image_paths) > 1:
            print(f"--- Processing image {i+1}/{len(args.image_paths)}: {image_path} ---")
        else:
            print(f"Processing image: {image_path}")

        try:
            output_fmt_enum = OutputFormat(args.format)
            neural_hash = calculate_neural_hash(image_path, output_fmt_enum)
            print(neural_hash)
            any_successful_processing = True
        except PyObjCNotAvailableError as e:
            # This should ideally be caught before the loop, but as a safeguard.
            print(f"Error: Critical PyObjC dependency missing: {e}", file=sys.stderr)
            exit_code = 1
            break # Fatal error for all processing
        except NeuralHashError as e:
            print(f"Error generating NeuralHash for '{image_path}': {e}", file=sys.stderr)
            exit_code = 1 # Mark as failure but continue with other images
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred with '{image_path}': {e}", file=sys.stderr)
            logger.exception("Unexpected error in CLI for %s", image_path) # Full traceback for debug
            exit_code = 1


        if len(args.image_paths) > 1 and i < len(args.image_paths) - 1:
            print("-" * 30)

    if pool: # Release the pool if it was created
        del pool

    if not any_successful_processing and args.image_paths:
        # If there were paths but none succeeded, ensure non-zero exit
        sys.exit(max(1, exit_code))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()