#!/bin/bash

set -x

poetry run autoflake \
  --recursive \
  --remove-all-unused-imports \
  --remove-unused-variables \
  --in-place bicycle_planner \
  --exclude=__init__.py

poetry run black bicycle_planner tests

poetry run isort bicycle_planner tests
