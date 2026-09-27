.PHONY: doctor dev test lint eval verify

doctor:
	python scripts/verify.py doctor

dev:
	python scripts/verify.py dev

test:
	python scripts/verify.py test

lint:
	python scripts/verify.py lint

eval:
	python scripts/verify.py eval

verify:
	python scripts/verify.py verify
