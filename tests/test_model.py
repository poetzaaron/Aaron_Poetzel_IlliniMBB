import numpy as np

from illiniportal import features
from illiniportal.model import TranslationModel


def test_fit_predict_shapes(synth_pairs):
    model = TranslationModel().fit(synth_pairs)
    assert set(model.metrics) <= set(features.usable_metrics(synth_pairs))
    proj = model.predict(synth_pairs)
    assert len(proj) == len(synth_pairs)
    for m in model.metrics:
        assert f"{m}_proj" in proj.columns


def test_coefficients_unique_per_metric(synth_pairs):
    model = TranslationModel().fit(synth_pairs)
    coefs = model.coefficients()
    real = coefs[~coefs["feature"].str.startswith("_")]
    assert not real.duplicated(["metric", "feature"]).any()


def test_save_load_roundtrip(synth_pairs, tmp_path):
    model = TranslationModel().fit(synth_pairs)
    path = tmp_path / "m.joblib"
    model.save(path)
    loaded = TranslationModel.load(path)
    a = model.predict(synth_pairs).to_numpy()
    b = loaded.predict(synth_pairs).to_numpy()
    assert np.allclose(np.nan_to_num(a), np.nan_to_num(b))
