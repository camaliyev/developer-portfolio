#!/usr/bin/env bash
# Render build command. Runs on every deploy.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
# Creates initial content only if missing; never overwrites admin edits.
python manage.py seed_portfolio
