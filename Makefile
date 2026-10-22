DEV = docker compose run --rm dev

.PHONY: up
up:
	@docker compose up --build -d gateway bank_simulator

.PHONY: down
down:
	@docker compose down

.PHONY: test
test:
	@$(DEV) sh -c "coverage run -m unittest discover -s tests -t . && coverage report"

.PHONY: lint
lint:
	@$(DEV) sh -c "ruff format --check . && ruff check . && mypy payment_gateway_api tests main.py"

.PHONY: format
format:
	@$(DEV) ruff format .

.PHONY: lock
lock:
	@$(DEV) poetry lock

# Needs `make up` first: real gateway + bank simulator.
.PHONY: e2e
e2e:
	@docker compose run --rm -e GATEWAY_URL=http://gateway:8000 dev python -m unittest discover -s tests/e2e -t . -v

.PHONY: perf
perf:
	@docker compose run --rm -e GATEWAY_URL=http://gateway:8000 dev python -m tests.performance.load_test --requests 500 --concurrency 20
