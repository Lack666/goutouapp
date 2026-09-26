.PHONY: doctor dev test eval verify

doctor:
	python scripts/verify.py doctor

dev:
	python scripts/verify.py dev

test:
	python scripts/verify.py test

eval:
	python scripts/verify.py eval

verify:
	python scripts/verify.py verify
