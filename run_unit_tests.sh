#!/bin/env sh

cd tests || exit 1

python build_test_infrastructure.py

python -m pytest
