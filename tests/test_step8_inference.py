"""Check that the HTTP and CLI paths use the same training preprocessing."""
import json
from pathlib import Path
import pandas as pd
import pytest
pytest.importorskip("flask")
from step8_deployment.app import app
from src.predict import score_file
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("count", [0, 10, 250])
def test_api_matches_cli(tmp_path, count):
    sample=json.loads((ROOT/'step8_deployment/sample_request.json').read_text())
    sample['prior_session_count']=count
    source=tmp_path/'sample.csv'; output=tmp_path/'result.csv'
    pd.DataFrame([sample]).to_csv(source,index=False)
    score_file(source,ROOT/'models/dial_alert_final_predictor.joblib',ROOT/'models/decision_threshold.json',output)
    response=app.test_client().post('/predict',json=sample)
    assert response.status_code == 200
    actual=response.get_json(); expected=pd.read_csv(output).iloc[0]
    assert actual['dial_alert_probability'] == pytest.approx(expected.dial_alert_probability,abs=1e-12)
    assert actual['dial_alert_flag'] == bool(expected.dial_alert_flag)

def test_bad_numeric_returns_400():
    sample=json.loads((ROOT/'step8_deployment/sample_request.json').read_text())
    sample['baseline_sbp']='invalid'
    assert app.test_client().post('/predict',json=sample).status_code == 400
