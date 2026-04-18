from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import REQUIRED_COLUMNS
from src.loader import (clean_column_values, convert_types,
                        detect_misplaced_specialist_type, load_data,
                        read_excel, validate_and_clean,
                        validate_categorical_values, validate_columns,
                        validate_score_range)

SAMPLE_DATA = Path(__file__).parent.parent / "data" / \
    "children_sessions (Data Scientist).xlsx"


@pytest.fixture
def valid_raw_df():
    """Минимально валидный сырой DataFrame."""
    data = {
        'child_id': ['СП01', 'СП01'],
        'age': [4, 4],
        'diagnosis': ['РАС, ур.2', 'РАС, ур.2'],
        'domain': ['Verbal_Request', 'Verbal_Request'],
        'session_date': ['15.01.2026', '10.02.2026'],
        'assessment_score': [3, 4],
        'comment': ['хорошо', 'прогресс'],
        'progress_flag': ['improved', 'improved'],
        'specialist_type': ['логопед', 'логопед'],
    }
    return pd.DataFrame(data)


@pytest.fixture
def df_with_misplaced_specialist():
    """DataFrame с ошибочно записанным specialist_type в progress_flag."""
    data = {
        'child_id': ['СП01', 'СП02'],
        'age': [4, 5],
        'diagnosis': ['РАС', 'РАС'],
        'domain': ['V', 'L'],
        'session_date': ['01.01.2026', '02.01.2026'],
        'assessment_score': [3, 4],
        'comment': ['', ''],
        'progress_flag': ['логопед', ''],
        'specialist_type': ['', 'дефектолог'],
    }
    return pd.DataFrame(data)


@pytest.fixture
def df_with_invalid_scores():
    """DataFrame с баллами вне диапазона."""
    data = {
        'child_id': ['СП01', 'СП02'],
        'age': [4, 5],
        'diagnosis': ['РАС', 'РАС'],
        'domain': ['V', 'L'],
        'session_date': ['01.01.2026', '02.01.2026'],
        'assessment_score': [0, 11],
        'comment': ['', ''],
        'progress_flag': ['', ''],
        'specialist_type': ['логопед', 'дефектолог'],
    }
    return pd.DataFrame(data)


def test_read_excel_success(tmp_path):
    """Успешное чтение существующего Excel-файла."""
    df_test = pd.DataFrame({'A': [1, 2]})
    file_path = tmp_path / "test.xlsx"
    df_test.to_excel(file_path, index=False)
    df = read_excel(file_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2


def test_read_excel_file_not_found():
    """Ошибка при отсутствии файла."""
    with pytest.raises(FileNotFoundError):
        read_excel("nonexistent.xlsx")


def test_validate_columns_success(valid_raw_df):
    """Все обязательные колонки присутствуют."""
    validate_columns(valid_raw_df)


def test_validate_columns_missing():
    """Отсутствие обязательной колонки вызывает ValueError."""
    df = pd.DataFrame({'child_id': ['СП01']})
    with pytest.raises(ValueError, match="Отсутствуют обязательные колонки"):
        validate_columns(df)


def test_detect_misplaced_specialist_type_correction(df_with_misplaced_specialist):
    """Ошибочный specialist_type переносится из progress_flag."""
    fixed_df = detect_misplaced_specialist_type(df_with_misplaced_specialist)
    assert fixed_df.loc[0, 'specialist_type'] == 'логопед'
    assert fixed_df.loc[0, 'progress_flag'] == ''
    assert fixed_df.loc[1, 'specialist_type'] == 'дефектолог'
    assert fixed_df.loc[1, 'progress_flag'] == ''


def test_detect_misplaced_specialist_type_no_change(valid_raw_df):
    """Корректные данные не изменяются."""
    original = valid_raw_df.copy()
    fixed_df = detect_misplaced_specialist_type(original)
    pd.testing.assert_frame_equal(fixed_df, original)


def test_clean_column_values_lowercase_strip():
    """Строки приводятся к нижнему регистру и обрезаются пробелы."""
    df = pd.DataFrame({
        'child_id': [' СП01 '],
        'diagnosis': ['РАС, Ур.2'],
        'domain': ['Verbal_Request'],
        'progress_flag': ['Improved'],
        'specialist_type': ['Логопед'],
        'comment': ['  Текст  '],
    })
    cleaned = clean_column_values(df)
    assert cleaned.loc[0, 'child_id'] == 'сп01'
    assert cleaned.loc[0, 'diagnosis'] == 'рас, ур.2'
    assert cleaned.loc[0, 'progress_flag'] == 'improved'
    assert cleaned.loc[0, 'specialist_type'] == 'логопед'
    assert cleaned.loc[0, 'comment'] == 'текст'


def test_clean_column_values_typo_correction():
    """Исправление опечаток в progress_flag."""
    df = pd.DataFrame({
        'child_id': ['СП01'],
        'diagnosis': ['РАС'],
        'domain': ['V'],
        'progress_flag': ['импровед'],
        'specialist_type': ['логопед'],
        'comment': [''],
    })
    cleaned = clean_column_values(df)
    assert cleaned.loc[0, 'progress_flag'] == 'improved'


def test_clean_column_values_specialist_correction():
    """Маппинг specialist_type через SPECIALIST_TYPE_CORRECTIONS."""
    df = pd.DataFrame({
        'child_id': ['СП01'],
        'diagnosis': ['РАС'],
        'domain': ['V'],
        'progress_flag': [''],
        'specialist_type': ['поведенческий аналитик'],
        'comment': [''],
    })
    cleaned = clean_column_values(df)
    assert cleaned.loc[0, 'specialist_type'] == 'па'


def test_validate_categorical_values_valid(valid_raw_df, caplog):
    """Допустимые категории не вызывают предупреждений."""
    df = clean_column_values(valid_raw_df.copy())
    validate_categorical_values(df)
    assert "Недопустимые значения" not in caplog.text


def test_validate_categorical_values_invalid_domain(caplog):
    """Неизвестный домен вызывает предупреждение."""
    df = pd.DataFrame({
        'child_id': ['СП01'],
        'diagnosis': ['РАС'],
        'domain': ['unknown_domain'],
        'progress_flag': [''],
        'specialist_type': ['логопед'],
        'comment': [''],
    })
    df = clean_column_values(df)
    validate_categorical_values(df)
    assert "Недопустимые значения в колонке 'domain'" in caplog.text


def test_validate_score_range_valid(valid_raw_df):
    """Баллы в диапазоне остаются без изменений."""
    df = valid_raw_df.copy()
    df['assessment_score'] = [3, 7]
    validate_score_range(df)
    assert df['assessment_score'].iloc[0] == 3
    assert df['assessment_score'].iloc[1] == 7


def test_validate_score_range_invalid(df_with_invalid_scores):
    """Баллы вне диапазона заменяются на NaN."""
    validate_score_range(df_with_invalid_scores)
    assert pd.isna(df_with_invalid_scores.loc[0, 'assessment_score'])
    assert pd.isna(df_with_invalid_scores.loc[1, 'assessment_score'])


def test_convert_types(valid_raw_df):
    """Проверка преобразования типов."""
    df = valid_raw_df.copy()
    df['session_date'] = ['15.01.2026', '10.02.2026']
    converted = convert_types(df)
    assert converted['age'].dtype == 'Int64'
    assert pd.api.types.is_numeric_dtype(converted['assessment_score'])
    assert pd.api.types.is_datetime64_any_dtype(converted['session_date'])
    assert converted['child_id'].dtype.name == 'category'


def test_validate_and_clean_removes_critical_nulls():
    """Удаление строк с пропущенными child_id, domain или session_date."""
    df = pd.DataFrame({
        'child_id': ['СП01', 'СП02'],
        'age': [4, 5],
        'diagnosis': ['РАС', 'РАС'],
        'domain': ['V', np.nan],
        'session_date': ['01.01.2026', '02.01.2026'],
        'assessment_score': [3, 4],
        'comment': ['', ''],
        'progress_flag': ['', ''],
        'specialist_type': ['логопед', 'дефектолог'],
    })
    cleaned = validate_and_clean(df)
    assert len(cleaned) == 1


def test_load_data_smoke():
    """Дымовой тест на реальных данных (если файл есть)."""
    if SAMPLE_DATA.exists():
        df = load_data(SAMPLE_DATA)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        for col in REQUIRED_COLUMNS:
            assert col in df.columns
    else:
        pytest.skip("Файл с данными отсутствует")


def test_load_data_returns_clean_data(tmp_path, valid_raw_df):
    """Проверяем, что load_data возвращает очищенные данные."""
    file_path = tmp_path / "test.xlsx"
    valid_raw_df.to_excel(file_path, index=False)
    df = load_data(file_path)
    assert df.loc[0, 'child_id'] == 'сп01'
    assert pd.api.types.is_datetime64_any_dtype(df['session_date'])
