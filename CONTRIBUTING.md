# Contributing

Thanks for considering a contribution.

## Development setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r backend/requirements.txt -r requirements-dev.txt`
3. Install the spaCy model:
   - `python -m spacy download en_core_web_sm`

## Run tests

- `python -m pytest -q`

## Code style

- `pre-commit run --all-files`

## Submitting changes

- Create a feature branch
- Keep commits small and conventional
- Open a pull request with a clear summary
