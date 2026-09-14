PYTHON ?= python
POETRY ?= poetry
STREAM_INTERVAL_SECONDS ?= 300
STREAM_MAX_COLLECTIONS ?= 15
STREAM_COLLECTION_INTERVAL_SECONDS ?= 1

.PHONY: install collect bronze-to-silver silver-to-gold run stream dashboard test lint format check clean-generated

install:
	$(POETRY) install

collect:
	$(POETRY) run python -m air_traffic_beam.collectors.aircraft_states --max-collections 1 --interval-seconds 1

bronze-to-silver:
	$(POETRY) run python -m air_traffic_beam.pipelines.bronze_to_silver --runner=DirectRunner --direct_num_workers=1

silver-to-gold:
	$(POETRY) run python -m air_traffic_beam.pipelines.silver_to_gold --runner=DirectRunner --direct_num_workers=1

run:
	$(POETRY) run python -m air_traffic_beam.run_all --max-collections 1 --interval-seconds 1

stream:
	@while true; do \
		$(POETRY) run python -m air_traffic_beam.run_all --max-collections $(STREAM_MAX_COLLECTIONS) --interval-seconds $(STREAM_COLLECTION_INTERVAL_SECONDS) || exit $$?; \
		echo "Próxima carga em $(STREAM_INTERVAL_SECONDS) segundos"; \
		sleep $(STREAM_INTERVAL_SECONDS); \
	done

dashboard:
	$(POETRY) run streamlit run src/air_traffic_beam/dashboard/app.py

test:
	$(POETRY) run pytest -q

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run ruff format .

check: lint test
	$(POETRY) run mypy src

clean-generated:
	find data -type d \( -path 'data/bronze' -o -path 'data/silver' -o -path 'data/gold' -o -path 'data/rejected' -o -path 'data/observability' \) -prune -o -type d -empty -delete
