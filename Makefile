test:
	python3 tests/run_tests.py python3 reference/main.py

autograder:
	python3 tools/build_autograder.py

grade:
	python3 tests/run_tests.py --dir tests/cases_hidden $(CMD)

.PHONY: test autograder grade
