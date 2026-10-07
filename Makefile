test:
	python3 tests/run_tests.py python3 reference/main.py

autograder:
	python3 tools/build_autograder.py

grade:
	python3 tests/run_tests.py --dir tests/cases_hidden $(CMD)

report:
	python3 tools/grade.py $(SUB)

report-batch:
	python3 tools/grade.py --batch $(DIR)

.PHONY: test autograder grade report report-batch
