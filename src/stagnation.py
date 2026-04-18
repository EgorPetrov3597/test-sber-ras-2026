"""
Модуль анализа застоя прогресса (stagnation) у детей по доменам навыков.

Основная функция:
- detect_stagnation(df, min_days=28) -> pd.DataFrame
  Возвращает отчёт с кейсами отсутствия прогресса за указанный период.
"""

import logging

import pandas as pd

logger = logging.getLogger(name=__name__)


def calculate_time_deltas(group: pd.DataFrame) -> pd.DataFrame:
    """
    Вычисляет разницу в баллах и днях между последовательными сессиями
    внутри группы (один ребёнок + один домен).

    Args:
        group: DataFrame, отсортированный по session_date.

    Returns:
        DataFrame с добавленными колонками:
        - days_since_prev: количество дней с предыдущей сессии
        - score_delta: изменение балла относительно предыдущей сессии
    """
    group = group.sort_values(by='session_date').copy()
    group['days_since_prev'] = group['session_date'].diff().dt.days
    group['score_delta'] = group['assessment_score'].diff()
    return group


def find_stagnation_periods(
    group: pd.DataFrame,
    min_days: int = 28
) -> list[dict]:
    """
    Ищет периоды застоя внутри группы (один ребёнок + один домен).

    Застой определяется как:
    - оценка не увеличивается (score_delta <= 0)
    - длительность периода (разница между первой и последней датой) >= min_days

    Args:
        group: DataFrame с колонками session_date, assessment_score, comment,
               days_since_prev, score_delta (после calculate_time_deltas).
        min_days: минимальная продолжительность периода без прогресса в днях.

    Returns:
        Список словарей с информацией о периодах застоя:
        - child_id
        - domain
        - start_date
        - end_date
        - duration_days
        - start_score
        - end_score
        - comments (конкатенация комментариев за период)
        - risk_level ('high', 'medium', 'low')
    """
    stagnation_periods = []
    group = group.sort_values(by='session_date').reset_index(drop=True)

    i = 0
    n = len(group)
    while i < n:
        # Пропускаем первую запись, так как нет предыдущей для сравнения
        if i == 0:
            i += 1
            continue

        current = group.iloc[i]

        # Проверяем отсутствие прогресса (оценка не выросла)
        if current['score_delta'] is not None and current['score_delta'] <= 0:
            # Начало потенциального периода застоя
            start_idx = i - 1
            end_idx = i
            # Расширяем период, пока оценка не растёт
            j = i + 1
            while j < n:
                next_row = group.iloc[j]
                if next_row['score_delta'] is not None and next_row['score_delta'] <= 0:
                    end_idx = j
                    j += 1
                else:
                    break

            # Вычисляем длительность периода
            start_date = group.iloc[start_idx]['session_date']
            end_date = group.iloc[end_idx]['session_date']
            duration = (end_date - start_date).days

            if duration >= min_days:
                # Собираем комментарии за период
                comments = ' | '.join(
                    group.iloc[start_idx:end_idx +
                               1]['comment'].dropna().astype(dtype=str)
                )

                # Определяем уровень риска
                if duration >= 60:
                    risk_level = 'high'
                elif duration >= 42:
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


def detect_stagnation(
    df: pd.DataFrame,
    min_days: int = 28
) -> pd.DataFrame:
    """
    Находит детей без прогресса по доменам за период не менее min_days.

    Анализ проводится для каждой комбинации (child_id, domain) отдельно.
    Прогресс определяется как увеличение assessment_score. Если оценка
    не растёт в течение >= min_days, такой период считается застоем.

    Args:
        df: DataFrame с колонками:
            - child_id (str)
            - domain (str)
            - session_date (datetime)
            - assessment_score (float/int)
            - comment (str)
        min_days: минимальное количество дней без прогресса для включения в отчёт.

    Returns:
        DataFrame с колонками:
        - child_id
        - domain
        - start_date
        - end_date
        - duration_days
        - start_score
        - end_score
        - comments
        - risk_level
        Строки соответствуют найденным периодам застоя. Если застоя нет,
        возвращается пустой DataFrame с указанными колонками.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            'child_id', 'domain', 'start_date', 'end_date',
            'duration_days', 'start_score', 'end_score',
            'comments', 'risk_level'
        ])

    required_cols = ['child_id', 'domain',
                     'session_date', 'assessment_score', 'comment']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")

    df_clean = df.dropna(subset=['session_date', 'assessment_score']).copy()
    if len(df_clean) < len(df):
        logger.warning(
            msg=f"Удалено {len(df) - len(df_clean)} записей с пропущенными датами или оценками"
        )

    all_periods = []
    # Группируем по ребёнку и домену
    for (child_id, domain), group in df_clean.groupby(by=['child_id', 'domain'], observed=True):
        if len(group) < 2:
            continue  # недостаточно данных для анализа динамики

        group_with_deltas = calculate_time_deltas(group=group)
        periods = find_stagnation_periods(
            group=group_with_deltas, min_days=min_days)
        all_periods.extend(periods)

    if not all_periods:
        return pd.DataFrame(columns=[...])

    result_df = pd.DataFrame(data=all_periods)

    if not result_df.empty:
        # Задаём упорядоченные категории: high < medium < low
        risk_order = pd.CategoricalDtype(
            categories=['high', 'medium', 'low'], ordered=True)
        result_df['risk_level'] = result_df['risk_level'].astype(
            dtype=risk_order)

        # Сортируем: сначала high, потом medium, потом low; внутри — по убыванию длительности
        result_df = result_df.sort_values(
            by=['risk_level', 'duration_days'],
            ascending=[True, False]
        )
        result_df = result_df.reset_index(drop=True)

    return result_df
