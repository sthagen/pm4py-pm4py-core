#!/bin/bash

set -e


echo "Cleaning previous builds..."
rm -rf build/
rm -rf source/api/

echo "1/2: Generating API documentation from Python source..."
sphinx-apidoc -e -o source/api ../pm4py/

echo "2/2: Building HTML files..."
sphinx-build -b html source build/html
