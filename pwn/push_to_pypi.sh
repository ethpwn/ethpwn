#!/bin/bash

source ~/.virtualenvs/ethpwn-build/bin/activate

python3 -m build

# if FOR_REALS is set, then we actually push to pypi, otherwise we push to TestPyPI
if [ -z "$FOR_REALS" ]; then
    echo "FOR_REALS not set, so we're pushing to TestPyPI"
    python3 -m twine upload -u __token__ --repository testpypi --skip-existing dist/*
else
    echo "FOR_REALS is set, so we're pushing to PyPI, are you sure? This is irreversible! If so, please type 'yes absolutely'"
    read -r answer
    if [ "$answer" != "yes absolutely" ]; then
        echo "Answer was not 'yes absolutely', so we're not pushing to PyPI"
        exit 1
    fi
    python3 -m twine upload -u __token__ --skip-existing dist/*
fi
