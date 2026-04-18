"""Модуль генерации отчётов и визуализации застоя прогресса."""

import logging
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logger = logging.getLogger(name=__name__)


def export_stagnation_report(
    stagnation_df: pd.DataFrame,
    output_path: Path,
    formats: List[str] = ["csv"]
) -> None:
    """
    Сохраняет отчёт о застое в CSV и/или Excel.

    Args:
        stagnation_df: DataFrame с результатами detect_stagnation.
        output_path: Базовый путь для сохранения (без расширения).
        formats: Список форматов: 'csv', 'excel'.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if "csv" in formats:
        csv_path = output_path.with_suffix(suffix=".csv")
        stagnation_df.to_csv(path_or_buf=csv_path,
                             index=False, encoding="utf-8-sig")
        logger.info(msg=f"CSV отчёт сохранён: {csv_path}")

    if "excel" in formats:
        excel_path = output_path.with_suffix(suffix=".xlsx")
        try:
            stagnation_df.to_excel(
                excel_writer=excel_path, index=False, engine="openpyxl")
            logger.info(msg=f"Excel отчёт сохранён: {excel_path}")
        except ImportError:
            logger.warning(
                msg="openpyxl не установлен, пропуск сохранения Excel.")


def plot_dynamics(
    df: pd.DataFrame,
    child_id: str,
    domain: str,
    output_dir: Path,
    highlight_stagnation: Optional[pd.DataFrame] = None
) -> Optional[Path]:
    """
    Строит график динамики баллов для конкретного ребёнка и домена.

    Args:
        df: Полный DataFrame с сессиями (после загрузки и очистки).
        child_id: Идентификатор ребёнка.
        domain: Домен навыка.
        output_dir: Директория для сохранения графика.
        highlight_stagnation: Опциональный DataFrame с периодами застоя
                              для подсветки на графике.

    Returns:
        Путь к сохранённому файлу PNG или None, если данных недостаточно.
    """
    mask = (df['child_id'] == child_id) & (df['domain'] == domain)
    child_data = df[mask].sort_values('session_date')

    if child_data.empty or len(child_data) < 2:
        logger.warning(
            msg=f"Недостаточно данных для графика: {child_id} {domain}")
        return None

    plt.figure(figsize=(10, 6))
    sns.set_style(style="whitegrid")

    # Основная линия
    ax = sns.lineplot(
        data=child_data,
        x='session_date',
        y='assessment_score',
        marker='o',
        linewidth=2,
        label='Оценка'
    )

    # Подсветка периодов застоя, если переданы
    if highlight_stagnation is not None and not highlight_stagnation.empty:
        periods = highlight_stagnation[
            (highlight_stagnation['child_id'] == child_id) &
            (highlight_stagnation['domain'] == domain)
        ]
        for _, period in periods.iterrows():
            ax.axvspan(
                xmin=period['start_date'],
                xmax=period['end_date'],
                alpha=0.2,
                color='red',
                label='Застой' if _ == 0 else ""
            )

    plt.title(label=f"Динамика баллов: {child_id} — {domain}")
    plt.xlabel(xlabel="Дата сессии")
    plt.ylabel(ylabel="Балл")
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{child_id}_{domain}_dynamics.png"
    filepath = output_dir / filename
    plt.savefig(filepath, dpi=150)
    plt.close()
    logger.info(msg=f"График сохранён: {filepath}")
    return filepath


def generate_summary_md(
    stagnation_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 5
) -> None:
    """
    Создаёт текстовый отчёт summary.md для супервизора.

    Args:
        stagnation_df: DataFrame с результатами застоя.
        output_path: Путь к файлу summary.md.
        top_n: Количество наиболее рискованных кейсов для выделения.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Отчёт о застое прогресса у детей с РАС",
        "",
        f"Дата генерации: {pd.Timestamp.now().strftime(format='%Y-%m-%d %H:%M')}",
        "",
        "## Общая статистика",
        "",
        f"- Всего периодов застоя: **{len(stagnation_df)}**",
        f"- Высокий риск (≥60 дней): **{len(stagnation_df[stagnation_df['risk_level'] == 'high'])}**",
        f"- Средний риск (42–59 дней): **{len(stagnation_df[stagnation_df['risk_level'] == 'medium'])}**",
        f"- Низкий риск (28–41 день): **{len(stagnation_df[stagnation_df['risk_level'] == 'low'])}**",
        "",
        "## Топ-{} кейсов, требующих внимания".format(top_n),
        ""
    ]

    if not stagnation_df.empty:
        top_cases = stagnation_df.head(top_n)
        for i, (_, row) in enumerate(iterable=top_cases.iterrows(), start=1):
            lines.extend([
                f"### {i}. {row['child_id']} — {row['domain']}",
                "",
                f"- **Период**: {row['start_date'].strftime('%d.%m.%Y')} – {row['end_date'].strftime('%d.%m.%Y')}",
                f"- **Длительность**: {row['duration_days']} дней",
                f"- **Уровень риска**: **{row['risk_level']}**",
                f"- **Баллы**: {row['start_score']} → {row['end_score']}",
                f"- **Комментарии**: {row['comments'] if row['comments'] else '—'}",
                "",
            ])
    else:
        lines.append("Застойных периодов не обнаружено. Позитивная динамика!")

    with open(file=output_path, mode="w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(msg=f"Текстовый отчёт сохранён: {output_path}")


def generate_all_reports(
    full_df: pd.DataFrame,
    stagnation_df: pd.DataFrame,
    output_dir: Path,
    top_n_plots: int = 5,
    formats: List[str] = ["csv"]
) -> None:
    """
    Создаёт все выходные артефакты: отчёты, графики, summary.

    Args:
        full_df: Полный DataFrame с сессиями.
        stagnation_df: Результат detect_stagnation.
        output_dir: Корневая директория для выходных файлов.
        top_n_plots: Количество кейсов с наивысшим риском для построения графиков.
        formats: Форматы для экспорта таблицы ('csv', 'excel').
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Табличный отчёт
    report_path = output_dir / "stagnation_report"
    export_stagnation_report(stagnation_df=stagnation_df,
                             output_path=report_path, formats=formats)

    # 2. Графики для топ-N кейсов
    plots_dir = output_dir / "plots"
    if not stagnation_df.empty:
        top_cases = stagnation_df.head(top_n_plots)
        for _, row in top_cases.iterrows():
            plot_dynamics(
                df=full_df,
                child_id=row['child_id'],
                domain=row['domain'],
                output_dir=plots_dir,
                highlight_stagnation=stagnation_df
            )

    # 3. Текстовый summary.md
    summary_path = output_dir / "summary.md"
    generate_summary_md(stagnation_df=stagnation_df,
                        output_path=summary_path, top_n=top_n_plots)
