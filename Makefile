.PHONY: install experiment benchmark publish publish-stats clean

RESULTS_ROOT ?= results

install:
	pip install -r requirements.txt

experiment:
	python -m src.cli experiment --region $${AWS_REGION:-us-east-1} --key-name $${KEY_NAME} --duration 180 --chunk-size 5 --out-root $(RESULTS_ROOT)/experiments

benchmark:
	python -m src.cli benchmark $${LOG_FILE} $${GROUND_TRUTH} --out-prefix $(RESULTS_ROOT)/benchmarks/bench --model o3-mini --manuscript docs/results/manuscript.md

publish:
	python -m src.cli publish $${EXP_DIR} --manuscript docs/results/manuscript.md

publish-stats:
	python -m src.cli publish_stats --results publication_ready_results.json --manuscript docs/results/manuscript.md

clean:
	rm -rf $(RESULTS_ROOT)/**/*.html $(RESULTS_ROOT)/**/*.png $(RESULTS_ROOT)/**/*.json || true







