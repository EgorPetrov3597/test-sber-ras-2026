"""Модуль загрузки и валидации данных из Excel-файла."""

import logging
from pathlib import Path
from typing import Union

import pandas as pd

from src.config import (ALLOWED_DOMAINS, ALLOWED_PROGRESS_FLAGS,
                        ALLOWED_SPECIALIST_TYPES, PROGRESS_FLAG_CORRECTIONS,
                        REQUIRED_COLUMNS, SCORE_MAX, SCORE_MIN,
                        SPECIALIST_TYPE_CORRECTIONS)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(name=__name__)


def read_excel(filepath: Union[str, Path]) -> pd.DataFrame:
    """Читает Excel-файл в pandas DataFrame."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Файл {filepath} не найден")

    try:
        df = pd.read_excel(io=filepath)
        logger.info(msg=f"Загружено {len(df)} записей из {filepath}")
        return df
    except Exception as e:
        raise ValueError(f"Ошибка чтения Excel-файла: {e}")


def validate_columns(df: pd.DataFrame) -> None:
    """Проверяет наличие всех обязательных колонок."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Отсутствуют обязательные колонки: {missing}")
    logger.info(msg="Проверка колонок пройдена")


def detect_misplaced_specialist_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Исправляет случаи, когда specialist_type ошибочно записан в progress_flag.
    """
    df = df.copy()
    possible_specialist_strings = list(SPECIALIST_TYPE_CORRECTIONS.keys())

    mask = (
        df['progress_flag'].str.lower().isin(values=possible_specialist_strings) &
        (df['specialist_type'].isna() | (df['specialist_type'] == ''))
    )

    if mask.any():
        logger.warning(
            msg=f"Обнаружено {mask.sum()} случаев, где specialist_type ошибочно записан в progress_flag. "
            "Выполняется перенос."
        )
        df.loc[mask, 'specialist_type'] = df.loc[mask, 'progress_flag'].apply(
            func=lambda x: SPECIALIST_TYPE_CORRECTIONS.get(x.lower(), '')
        )
        df.loc[mask, 'progress_flag'] = ''

    return df


def clean_column_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Приводит строковые колонки к нижнему регистру, удаляет пробелы, исправляет опечатки.
    """
    df = df.copy()
    str_columns = ['child_id', 'diagnosis', 'domain',
                   'progress_flag', 'specialist_type', 'comment']
    for col in str_columns:
        if col in df.columns:
            # Преобразуем в строку, убираем пробелы, в нижний регистр
            df[col] = df[col].astype(dtype=str).str.strip().str.lower()
            df[col] = df[col].replace(to_replace={'nan': '', 'none': ''})
            df[col] = df[col].fillna(value='')

    # Исправляем опечатки в progress_flag
    if 'progress_flag' in df.columns:
        df['progress_flag'] = df['progress_flag'].replace(
            PROGRESS_FLAG_CORRECTIONS)
        df['progress_flag'] = df['progress_flag'].fillna(value='')

    # Исправляем specialist_type через маппинг
    if 'specialist_type' in df.columns:
        df['specialist_type'] = df['specialist_type'].apply(
            func=lambda x: SPECIALIST_TYPE_CORRECTIONS.get(
                x, x) if pd.notna(x) else ''
        )
        df['specialist_type'] = df['specialist_type'].fillna(value='')

    return df


def validate_categorical_values(df: pd.DataFrame) -> None:
    """Проверяет, что категориальные значения принадлежат допустимым множествам."""
    invalid_domains = set(df['domain'].unique()) - ALLOWED_DOMAINS
    if invalid_domains:
        logger.warning(
            msg=f"Недопустимые значения в колонке 'domain': {invalid_domains}")

    invalid_flags = set(df['progress_flag'].unique()) - ALLOWED_PROGRESS_FLAGS
    if invalid_flags:
        logger.warning(
            msg=f"Недопустимые значения в колонке 'progress_flag': {invalid_flags}")

    invalid_specialists = set(
        df['specialist_type'].unique()) - ALLOWED_SPECIALIST_TYPES
    if invalid_specialists:
        logger.warning(
            msg=f"Недопустимые значения в колонке 'specialist_type': {invalid_specialists}")


def validate_score_range(df: pd.DataFrame) -> None:
    """Проверяет диапазон assessment_score [1, 10]."""
    df['assessment_score'] = pd.to_numeric(
        arg=df['assessment_score'], errors='coerce')
    invalid_scores = df[
        (df['assessment_score'] < SCORE_MIN) | (
            df['assessment_score'] > SCORE_MAX)
    ]
    if not invalid_scores.empty:
        logger.warning(
            msg=f"Обнаружено {len(invalid_scores)} записей с assessment_score вне диапазона "
            f"[{SCORE_MIN}, {SCORE_MAX}]. Они будут заменены на NaN."
        )
        df.loc[invalid_scores.index, 'assessment_score'] = pd.NA


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит колонки к правильным типам данных."""
    df = df.copy()
    df['age'] = pd.to_numeric(df['age'], errors='coerce').astype(dtype='Int64')
    df['assessment_score'] = pd.to_numeric(
        df['assessment_score'], errors='coerce')
    df['session_date'] = pd.to_datetime(
        df['session_date'], errors='coerce', dayfirst=True)
    for col in ['child_id', 'diagnosis', 'domain', 'progress_flag', 'specialist_type']:
        if col in df.columns:
            df[col] = df[col].astype(dtype='category')
    return df


def validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Основная функция валидации и очистки данных."""
    validate_columns(df=df)
    df = detect_misplaced_specialist_type(df=df)
    df = clean_column_values(df=df)
    validate_categorical_values(df=df)
    validate_score_range(df=df)
    df = convert_types(df=df)

    critical_nulls = df[['child_id', 'domain',
                         'session_date']].isnull().any(axis=1)
    if critical_nulls.any():
        logger.warning(
            msg=f"Обнаружено {critical_nulls.sum()} записей с пропусками в критических полях. "
            "Они будут удалены."
        )
        df = df[~critical_nulls]

    logger.info(msg=f"После очистки осталось {len(df)} записей")
    return df


def load_data(filepath: Union[str, Path]) -> pd.DataFrame:
    """Загружает данные, проводит валидацию и очистку."""
    raw_df = read_excel(filepath=filepath)
    clean_df = validate_and_clean(df=raw_df)
    return clean_df
