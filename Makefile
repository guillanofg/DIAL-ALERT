.PHONY: setup data build train assets audit report test reproduce

setup:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

data:
	python src/download_data.py

build:
	python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed

train:
	python src/train_evaluate.py --data data/processed/hemobp_session_level.csv.gz --config configs/model_config.json --artifacts artifacts --models models

assets:
	python src/generate_eda.py
	python src/generate_step4_assets.py

audit:
	python src/audit_bias_fairness.py

report:
	python src/create_final_report.py

test:
	pytest -q

reproduce: data build train assets audit report test

