#!/bin/bash

set -ex

poetry run black --check --diff bicycle_planner tests
poetry run flake8 bicycle_planner tests
poetry run isort --check-only bicycle_planner tests
poetry run mypy bicycle_planner
