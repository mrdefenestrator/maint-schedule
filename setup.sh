#!/usr/bin/env bash
set -eu

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
