"""Модуль анализа застоя прогресса (stagnation) у детей по доменам навыков."""

import logging
from typing import List

import numpy as np
import pandas as pd

from src.config import RISK_HIGH_DAYS, RISK_MEDIUM_DAYS, STAGNATION_KEYWORDS

logger = logging.getLogger(name=__name__)


def calculate_time_deltas(group: pd.DataFrame) -> pd.DataFrame:
    """
    Вычисляет разницу в баллах и днях между последовательными сессиями
    внутри группы (один ребёнок + один домен).
    """
    group = group.sort_values(by='session_date').copy()
    group['days_since_prev'] = group['session_date'].diff().dt.days
    group['score_delta'] = group['assessment_score'].diff()
    return group


def find_stagnation_periods(
    group: pd.DataFrame,
    min_days: int = 28,
    risk_high_days: int = RISK_HIGH_DAYS,
    risk_medium_days: int = RISK_MEDIUM_DAYS
) -> List[dict]:
    """
    Ищет периоды застоя внутри группы (один ребёнок + один домен).

    Застой определяется как:
    - оценка не увеличивается (score_delta <= 0)
    - длительность периода (разница между первой и последней датой) >= min_days

    Returns:
        Список словарей с информацией о периодах застоя.
    """
    stagnation_periods = []
    group = group.sort_values(by='session_date').reset_index(drop=True)

    i = 0
    n = len(group)
    while i < n:
        if i == 0:
            i += 1
            continue

        current = group.iloc[i]
        if current['score_delta'] is not None and current['score_delta'] <= 0:
            start_idx = i - 1
            end_idx = i
            j = i + 1
            while j < n:
                next_row = group.iloc[j]
                if next_row['score_delta'] is not None and next_row['score_delta'] <= 0:
                    end_idx = j
                    j += 1
                else:
                    break

            start_date = group.iloc[start_idx]['session_date']
            end_date = group.iloc[end_idx]['session_date']
            duration = (end_date - start_date).days

            if duration >= min_days:
                comments = ' | '.join(
                    group.iloc[start_idx:end_idx +
                               1]['comment'].dropna().astype(dtype=str)
                )

                if duration >= risk_high_days:
                    risk_level = 'high'
                elif duration >= risk_medium_days:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'

                period_info = {
                    'child_id': group.iloc[0]['child_id'],
                    'domain': group.iloc[0]['domain'],
                    'start_date': start_date,
                    'end_date': end_date,
                    'duration_days': duration,
                    'start_score': group.iloc[start_idx]['assessment_score'],
                    'end_score': group.iloc[end_idx]['assessment_score'],
                    'comments': comments,
                    'risk_level': risk_level
                }
                stagnation_periods.append(period_info)

            i = end_idx + 1
        else:
            i += 1

    return stagnation_periods


def analyze_comments_for_stagnation(comments: str) -> tuple[List[str], bool]:
    """
    Анализирует строку комментариев на наличие ключевых слов стагнации.

    Args:
        comments: Строка с комментариями (уже в нижнем регистре).

    Returns:
        Кортеж (список найденных ключевых слов, флаг наличия хотя бы одного).
    """
    if not comments or pd.isna(comments):
        return [], False
    comments_lower = comments.lower()
    found = [kw for kw in STAGNATION_KEYWORDS if kw in comments_lower]
    has_any = bool(len(found) > 0)
    return found, has_any


def detect_stagnation(
    df: pd.DataFrame,
    min_days: int = 28,
    use_comment_analysis: bool = False,
    risk_high_days: int = RISK_HIGH_DAYS,
    risk_medium_days: int = RISK_MEDIUM_DAYS
) -> pd.DataFrame:
    """
    Находит детей без прогресса по доменам за период не менее min_days.

    Args:
        df: DataFrame с колонками child_id, domain, session_date, assessment_score, comment.
        min_days: минимальное количество дней без прогресса.
        use_comment_analysis: если True, анализирует комментарии на ключевые слова стагнации
                              и добавляет колонки 'stagnation_indicators' и 'has_stagnation_comment'.

    Returns:
        DataFrame с периодами застоя. Если use_comment_analysis=True, добавляются колонки
        'stagnation_indicators' (список) и 'has_stagnation_comment' (bool).
    """
    base_columns = [
        'child_id', 'domain', 'start_date', 'end_date',
        'duration_days', 'start_score', 'end_score', 'comments', 'risk_level'
    ]
    if use_comment_analysis:
        base_columns.extend(
            ['stagnation_indicators', 'has_stagnation_comment'])

    if df.empty:
        return pd.DataFrame(columns=base_columns)

    required_cols = ['child_id', 'domain',
                     'session_date', 'assessment_score', 'comment']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")

    df_clean = df.dropna(subset=['session_date', 'assessment_score']).copy()
    if len(df_clean) < len(df):
        logger.warning(
            f"Удалено {len(df) - len(df_clean)} записей с пропущенными датами или оценками"
        )

    all_periods = []
    for (child_id, domain), group in df_clean.groupby(by=['child_id', 'domain'], observed=True):
        if len(group) < 2:
            continue

        group_with_deltas = calculate_time_deltas(group=group)
        periods = find_stagnation_periods(
            group=group_with_deltas,
            min_days=min_days,
            risk_high_days=risk_high_days,
            risk_medium_days=risk_medium_days)

        for period in periods:
            if use_comment_analysis:
                indicators, has_indicator = analyze_comments_for_stagnation(
                    period['comments'])
                period['stagnation_indicators'] = indicators
                period['has_stagnation_comment'] = has_indicator
            all_periods.append(period)

    if not all_periods:
        return pd.DataFrame(columns=base_columns)

    result_df = pd.DataFrame(data=all_periods)

    if not result_df.empty:
        if 'has_stagnation_comment' in result_df.columns:
            result_df['has_stagnation_comment'] = result_df['has_stagnation_comment'].astype(
                dtype=bool)
        risk_order = pd.CategoricalDtype(
            categories=['high', 'medium', 'low'], ordered=True)
        result_df['risk_level'] = result_df['risk_level'].astype(
            dtype=risk_order)
        result_df = result_df.sort_values(
            by=['risk_level', 'duration_days'],
            ascending=[True, False]
        )
        result_df = result_df.reset_index(drop=True)

    for col in base_columns:
        if col not in result_df.columns:
            result_df[col] = np.nan if col not in [
                'stagnation_indicators'] else [[] for _ in range(len(result_df))]

    return result_df[base_columns]
