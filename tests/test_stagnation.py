"""Unit-тесты для модуля stagnation.py."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.stagnation import (calculate_time_deltas, detect_stagnation,
                            find_stagnation_periods)


@pytest.fixture
def sample_group_with_stagnation():
    """Группа (один ребёнок + домен) с явным периодом застоя."""
    dates = [
        datetime(year=2026, month=1, day=1),
        datetime(year=2026, month=1, day=15),
        datetime(year=2026, month=2, day=1),
        datetime(year=2026, month=3, day=1),
        datetime(year=2026, month=3, day=15),
    ]
    scores = [3, 3, 3, 4, 4]  # застой с 1 янв по 1 фев (31 день)
    comments = ["c1", "c2", "c3", "c4", "c5"]
    df = pd.DataFrame(data={
        'child_id': ['СП01'] * 5,
        'domain': ['Verbal_Request'] * 5,
        'session_date': dates,
        'assessment_score': scores,
        'comment': comments,
    })
    return df


@pytest.fixture
def sample_group_no_stagnation():
    """Группа с постоянным прогрессом (нет застоя)."""
    dates = [
        datetime(year=2026, month=1, day=1),
        datetime(year=2026, month=1, day=15),
        datetime(year=2026, month=2, day=1),
    ]
    scores = [2, 4, 6]
    df = pd.DataFrame(data={
        'child_id': ['СП02'] * 3,
        'domain': ['Listening'] * 3,
        'session_date': dates,
        'assessment_score': scores,
        'comment': ['a', 'b', 'c'],
    })
    return df


@pytest.fixture
def sample_df_multi_child():
    """Датафрейм с несколькими детьми и доменами."""
    data = {
        'child_id': ['СП01', 'СП01', 'СП01', 'СП02', 'СП02', 'СП02', 'СП03', 'СП03'],
        'domain': ['V', 'V', 'V', 'L', 'L', 'L', 'S', 'S'],
        'session_date': [
            datetime(year=2026, month=1, day=1), datetime(year=2026, month=1, day=20), datetime(
                year=2026, month=2, day=15),  # СП01 V: рост
            datetime(year=2026, month=1, day=5), datetime(year=2026, month=2, day=5), datetime(
                year=2026, month=3, day=5),    # СП02 L: застой (2 мес)
            # СП03 S: мало данных
            datetime(year=2026, month=1, day=10), datetime(
                year=2026, month=2, day=10),
        ],
        'assessment_score': [3, 4, 5, 7, 7, 7, 2, 3],
        'comment': ['c1', 'c2', 'c3', 'd1', 'd2', 'd3', 'e1', 'e2'],
    }
    return pd.DataFrame(data)


def test_calculate_time_deltas(sample_group_with_stagnation):
    """Проверяет вычисление дельт дней и баллов."""
    result = calculate_time_deltas(group=sample_group_with_stagnation)
    assert 'days_since_prev' in result.columns
    assert 'score_delta' in result.columns
    # Проверяем первую строку (NaN для diff)
    assert pd.isna(result.iloc[0]['days_since_prev'])
    assert pd.isna(result.iloc[0]['score_delta'])
    # Вторая строка: 14 дней, дельта 0
    assert result.iloc[1]['days_since_prev'] == 14
    assert result.iloc[1]['score_delta'] == 0
    # Третья строка: с 15 янв по 1 фев = 17 дней
    assert result.iloc[2]['days_since_prev'] == 17


def test_calculate_time_deltas_single_row():
    """Если в группе только одна запись, дельты остаются NaN."""
    df = pd.DataFrame(data={
        'child_id': ['СП01'],
        'domain': ['V'],
        'session_date': [datetime(year=2026, month=1, day=1)],
        'assessment_score': [5],
        'comment': [''],
    })
    result = calculate_time_deltas(group=df)
    assert len(result) == 1
    assert pd.isna(result.iloc[0]['days_since_prev'])
    assert pd.isna(result.iloc[0]['score_delta'])


def test_find_stagnation_periods_found(sample_group_with_stagnation):
    """Находит период застоя в группе с плато."""
    group_with_deltas = calculate_time_deltas(
        group=sample_group_with_stagnation)
    periods = find_stagnation_periods(group=group_with_deltas, min_days=28)
    assert len(periods) == 1
    p = periods[0]
    assert p['child_id'] == 'СП01'
    assert p['domain'] == 'Verbal_Request'
    assert p['start_date'] == datetime(year=2026, month=1, day=1)
    assert p['end_date'] == datetime(year=2026, month=2, day=1)
    assert p['duration_days'] == 31
    assert p['start_score'] == 3
    assert p['end_score'] == 3
    assert p['risk_level'] == 'low'
    assert 'c1' in p['comments'] and 'c3' in p['comments']


def test_find_stagnation_periods_none(sample_group_no_stagnation):
    """Не находит застоя, если прогресс идёт постоянно."""
    group_with_deltas = calculate_time_deltas(group=sample_group_no_stagnation)
    periods = find_stagnation_periods(group=group_with_deltas, min_days=28)
    assert len(periods) == 0


def test_find_stagnation_periods_risk_levels():
    """Проверяет назначение уровней риска по длительности."""
    base_date = datetime(year=2026, month=1, day=1)
    test_cases = [
        (30, 'low', 28, 60, 42),
        (45, 'medium', 28, 60, 42),
        (65, 'high', 28, 60, 42),
        (50, 'high', 28, 50, 30),   # при risk_high=50
        (50, 'medium', 28, 70, 40),  # при risk_high=70, risk_medium=40
    ]
    for duration, expected_risk, min_days, high_days, medium_days in test_cases:
        dates = [base_date, base_date + timedelta(days=duration)]
        scores = [5, 5]
        df = pd.DataFrame(data={
            'child_id': ['СП01', 'СП01'],
            'domain': ['V', 'V'],
            'session_date': dates,
            'assessment_score': scores,
            'comment': ['', ''],
        })
        group_with_deltas = calculate_time_deltas(group=df)
        periods = find_stagnation_periods(
            group=group_with_deltas,
            min_days=min_days,
            risk_high_days=high_days,
            risk_medium_days=medium_days
        )
        assert len(periods) == 1
        assert periods[0]['risk_level'] == expected_risk


def test_find_stagnation_periods_min_days_threshold():
    """Не включает периоды короче min_days."""
    dates = [datetime(year=2026, month=1, day=1), datetime(
        year=2026, month=1, day=20)]  # 19 дней
    scores = [5, 5]
    df = pd.DataFrame(data={
        'child_id': ['СП01', 'СП01'],
        'domain': ['V', 'V'],
        'session_date': dates,
        'assessment_score': scores,
        'comment': ['', ''],
    })
    group_with_deltas = calculate_time_deltas(group=df)
    periods_default = find_stagnation_periods(
        group=group_with_deltas, min_days=28)
    assert len(periods_default) == 0
    periods_custom = find_stagnation_periods(
        group=group_with_deltas, min_days=15)
    assert len(periods_custom) == 1


def test_find_stagnation_periods_multiple_periods():
    """Группа с двумя разделёнными периодами застоя."""
    dates = [
        datetime(year=2026, month=1, day=1),
        datetime(year=2026, month=2, day=1),  # застой 31 день
        datetime(year=2026, month=2, day=15),
        datetime(year=2026, month=3, day=20),  # рост, затем снова застой
        datetime(year=2026, month=4, day=20),  # застой 31 день
    ]
    scores = [4, 4, 5, 5, 5]
    df = pd.DataFrame(data={
        'child_id': ['СП01'] * 5,
        'domain': ['M'] * 5,
        'session_date': dates,
        'assessment_score': scores,
        'comment': [''] * 5,
    })
    group_with_deltas = calculate_time_deltas(group=df)
    periods = find_stagnation_periods(group=group_with_deltas, min_days=28)
    assert len(periods) == 2
    assert periods[0]['start_date'] == datetime(year=2026, month=1, day=1)
    # Второй период начинается с первой точки плато (2026-02-15)
    assert periods[1]['start_date'] == datetime(year=2026, month=2, day=15)


def test_detect_stagnation_basic(sample_df_multi_child):
    """Интеграционный тест на полном датафрейме."""
    result = detect_stagnation(df=sample_df_multi_child, min_days=28,
                               risk_high_days=60,
                               risk_medium_days=42)
    assert isinstance(result, pd.DataFrame)
    # Ожидаем один период застоя: СП02 L (1.5 - 5.3) ~ 59 дней, риск medium
    assert len(result) == 1
    row = result.iloc[0]
    assert row['child_id'] == 'СП02'
    assert row['domain'] == 'L'
    assert row['duration_days'] == 59
    assert row['risk_level'] == 'medium'


def test_detect_stagnation_empty_input():
    """Возвращает пустой DataFrame с правильными колонками."""
    empty_df = pd.DataFrame(
        columns=['child_id', 'domain', 'session_date', 'assessment_score', 'comment'])
    result = detect_stagnation(df=empty_df)
    assert result.empty
    expected_cols = ['child_id', 'domain', 'start_date', 'end_date',
                     'duration_days', 'start_score', 'end_score', 'comments', 'risk_level']
    assert list(result.columns) == expected_cols


def test_detect_stagnation_insufficient_data():
    """Если у ребёнка только одна сессия, застой не определяется."""
    df = pd.DataFrame(data={
        'child_id': ['СП01'],
        'domain': ['V'],
        'session_date': [datetime(year=2026, month=1, day=1)],
        'assessment_score': [5],
        'comment': [''],
    })
    result = detect_stagnation(df=df)
    assert result.empty


def test_detect_stagnation_missing_values_dropped():
    """Строки с пропущенными датами или баллами исключаются из анализа."""
    df = pd.DataFrame(data={
        'child_id': ['СП01', 'СП01', 'СП01'],
        'domain': ['V', 'V', 'V'],
        'session_date': [datetime(year=2026, month=1, day=1), None, datetime(year=2026, month=3, day=1)],
        'assessment_score': [3, 4, 5],
        'comment': ['', '', ''],
    })
    result = detect_stagnation(df=df, min_days=10)
    # После удаления строки с None останется две сессии (1 янв и 1 мар), но между ними рост
    assert result.empty


def test_detect_stagnation_custom_min_days():
    """Параметр min_days влияет на результат."""
    dates = [datetime(year=2026, month=1, day=1), datetime(
        year=2026, month=1, day=20)]  # 19 дней
    scores = [3, 3]
    df = pd.DataFrame(data={
        'child_id': ['СП01', 'СП01'],
        'domain': ['V', 'V'],
        'session_date': dates,
        'assessment_score': scores,
        'comment': ['', ''],
    })
    assert detect_stagnation(df=df, min_days=28).empty
    assert not detect_stagnation(df=df, min_days=15).empty


def test_detect_stagnation_sorting():
    """Результат сортируется по убыванию риска и длительности."""
    data = {
        'child_id': ['A', 'A', 'B', 'B', 'C', 'C'],
        'domain': ['d1', 'd1', 'd2', 'd2', 'd3', 'd3'],
        'session_date': [
            datetime(year=2026, month=1, day=1), datetime(
                year=2026, month=2, day=1),   # 31 день low
            datetime(year=2026, month=1, day=1), datetime(
                year=2026, month=3, day=1),   # 59 дней medium
            datetime(year=2026, month=1, day=1), datetime(
                year=2026, month=4, day=1),   # 90 дней high
        ],
        'assessment_score': [3, 3, 5, 5, 7, 7],
        'comment': [''] * 6,
    }
    df = pd.DataFrame(data=data)
    result = detect_stagnation(df=df, min_days=28,                                risk_high_days=60,
                               risk_medium_days=42)
    assert len(result) == 3
    # Ожидаемый порядок: high, medium, low
    assert list(result['risk_level']) == ['high', 'medium', 'low']
    # При одинаковом риске (low нет) порядок по длительности убывающий
    # Здесь все риски разные, проверяем сортировку по длительности внутри риска дополнительно не требуется.


def test_detect_stagnation_with_comment_analysis():
    """Проверяет, что при use_comment_analysis=True добавляются нужные колонки и находятся индикаторы."""
    data = {
        'child_id': ['СП01', 'СП01'],
        'domain': ['V', 'V'],
        'session_date': [datetime(year=2026, month=1, day=1), datetime(year=2026, month=2, day=1)],
        'assessment_score': [3, 3],
        'comment': ['Плато, нет прогресса', 'стабильный уровень'],
    }
    df = pd.DataFrame(data=data)
    result = detect_stagnation(df=df, min_days=28, use_comment_analysis=True)
    assert len(result) == 1
    row = result.iloc[0]
    assert 'stagnation_indicators' in result.columns
    assert 'has_stagnation_comment' in result.columns
    assert row['has_stagnation_comment'] == True
    assert 'плато' in row['stagnation_indicators']
    assert 'нет прогресса' in row['stagnation_indicators']


def test_detect_stagnation_without_comment_analysis():
    """Без флага колонки анализа комментариев не добавляются."""
    data = {
        'child_id': ['СП01', 'СП01'],
        'domain': ['V', 'V'],
        'session_date': [datetime(year=2026, month=1, day=1), datetime(year=2026, month=2, day=1)],
        'assessment_score': [3, 3],
        'comment': ['Плато', ''],
    }
    df = pd.DataFrame(data)
    result = detect_stagnation(df=df, min_days=28, use_comment_analysis=False)
    assert 'stagnation_indicators' not in result.columns
    assert 'has_stagnation_comment' not in result.columns


def test_analyze_comments_no_stagnation():
    """Комментарии без ключевых слов не дают индикаторов."""
    data = {
        'child_id': ['СП01', 'СП01'],
        'domain': ['V', 'V'],
        'session_date': [datetime(year=2026, month=1, day=1), datetime(year=2026, month=2, day=1)],
        'assessment_score': [3, 3],
        'comment': ['Всё хорошо', 'Ребёнок старается'],
    }
    df = pd.DataFrame(data=data)
    result = detect_stagnation(df=df, min_days=28, use_comment_analysis=True)
    assert len(result) == 1
    assert result.iloc[0]['has_stagnation_comment'] == False
    assert result.iloc[0]['stagnation_indicators'] == []


def test_detect_stagnation_custom_risk_thresholds():
    """Проверяет, что пороги риска можно переопределить."""
    data = {
        'child_id': ['A', 'A'],
        'domain': ['d1', 'd1'],
        # 40 дней
        'session_date': [datetime(year=2026, month=1, day=1), datetime(year=2026, month=2, day=10)],
        'assessment_score': [5, 5],
        'comment': ['', ''],
    }
    df = pd.DataFrame(data=data)
    # По умолчанию 40 дней — low
    result_default = detect_stagnation(df=df, min_days=28)
    assert result_default.iloc[0]['risk_level'] == 'low'
    # Если снизить порог high до 40 дней — станет high
    result_custom = detect_stagnation(df=df, min_days=28, risk_high_days=40)
    assert result_custom.iloc[0]['risk_level'] == 'high'
