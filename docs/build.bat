@echo off

echo Cleaning previous builds...
if exist build\ rmdir /s /q build
if exist source\api\ rmdir /s /q source\api

echo 1/2: Generating API documentation from Python source...
sphinx-apidoc -e -o source\api ..\pm4py\ || exit /b

echo 2/2: Building HTML files...
sphinx-build -b html source build\html || exit /b
