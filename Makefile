.PHONY: setup test benchmark quantum-lab train evaluate migration-demo demo api frontend lint

PY := .venv/Scripts/python.exe

setup:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

test:
	cd backend && ../$(PY) -m pytest -v

benchmark:
	cd backend && ../$(PY) -m app.benchmarks.run_all

quantum-lab:
	cd backend && ../$(PY) -m app.quantum.grover_lab
	cd backend && ../$(PY) -m app.quantum.shor_lab

train:
	cd backend && ../$(PY) -m app.ai.train

evaluate:
	cd backend && ../$(PY) -m app.ai.model_registry

migration-demo:
	cd backend && ../$(PY) -m app.discovery.scanner
	cd backend && ../$(PY) -m app.risk.service
	cd backend && ../$(PY) -m app.recommendations.engine
	cd backend && ../$(PY) -m app.migration.planner
	cd backend && ../$(PY) -m app.migration.simulator

demo:
	cd backend && ../$(PY) -m scripts.run_demo

api:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

lint:
	cd backend && ../$(PY) -m ruff check app

research:
	$(PY) -m research.generate_report_assets

exp6:
	$(PY) -m research.experiments.exp6_crypto_agility

ablation:
	$(PY) -m research.experiments.ablation_risk_features

noise-analysis:
	$(PY) -m research.experiments.exp8_noise_analysis

significance:
	$(PY) -m research.experiments.significance_testing

benchmark-info-ablation:
	$(PY) -m research.experiments.ablation_benchmark_info

ai-model-ablation:
	$(PY) -m research.experiments.ablation_ai_model

explainability-ablation:
	$(PY) -m research.experiments.ablation_explainability
