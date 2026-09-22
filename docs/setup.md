# Setup Guide

## System Requirements
- Python 3.11+
- System C/C++ compiler (`gcc` or `clang`)
- `libclang` system shared object (`libclang.so` / `libclang.dylib` / `libclang.dll`)

## Installation
```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]