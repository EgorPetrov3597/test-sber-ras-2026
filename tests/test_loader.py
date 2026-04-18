from pathlib import Path

import pandas as pd
import pytest

from src.loader import detect_misplaced_specialist_type, load_data

SAMPLE_DATA = Path(__file__).parent.parent / "data" / \
    "children_sessions (Data Scientist).xlsx"


def test_load_data_smoke():
    """Дымовой тест: проверяем, что данные загружаются без исключений."""
    if SAMPLE_DATA.exists():
        df = load_data(SAMPLE_DATA)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
    else:
        pytest.skip("Файл с данными отсутствует")


def test_detect_misplaced_specialist_type():
    """Тест исправления смещённого specialist_type."""
    df = pd.DataFrame({
        'progress_flag': ['логопед', 'improved', ''],
        'specialist_type': ['', 'дефектолог', 'ПА']
    })
    fixed = detect_misplaced_specialist_type(df)
    assert fixed.loc[0, 'specialist_type'] == 'логопед'
    assert fixed.loc[0, 'progress_flag'] == ''
    assert fixed.loc[1, 'specialist_type'] == 'дефектолог'
