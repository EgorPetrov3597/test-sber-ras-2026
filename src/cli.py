"""Интерфейс командной строки для анализа застоя прогресса."""

import logging
from pathlib import Path

import click

from src.loader import load_data
from src.report_generator import generate_all_reports
from src.stagnation import detect_stagnation

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(name=__name__)


@click.command()
@click.option(
    '--input', '-i',
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help='Путь к входному Excel-файлу (children_sessions.xlsx).'
)
@click.option(
    '--output', '-o',
    type=click.Path(file_okay=False, path_type=Path),
    default=Path('output'),
    show_default=True,
    help='Директория для сохранения результатов.'
)
@click.option(
    '--min-days',
    type=int,
    default=28,
    show_default=True,
    help='Минимальная длительность застоя в днях.'
)
@click.option(
    '--top-n',
    type=int,
    default=5,
    show_default=True,
    help='Количество кейсов с наивысшим риском для построения графиков.'
)
@click.option(
    '--formats',
    type=click.Choice(choices=['csv', 'excel', 'both'], case_sensitive=False),
    default='csv',
    show_default=True,
    help='Формат сохранения табличного отчёта.'
)
@click.option(
    '--comment-analysis/--no-comment-analysis',
    default=False,
    show_default=True,
    help='Анализировать комментарии на ключевые слова стагнации.'
)
@click.option(
    '--risk-high',
    type=int,
    default=60,
    show_default=True,
    help='Порог высокого риска (дней).'
)
@click.option(
    '--risk-medium',
    type=int,
    default=42,
    show_default=True,
    help='Порог среднего риска (дней).'
)
@click.option(
    '--interactive', '-I',
    is_flag=True,
    help='Запустить в интерактивном режиме (запрос параметров через консоль).'
)
def analyze(
    input: Path,
    output: Path,
    min_days: int,
    top_n: int,
    formats: str,
    comment_analysis: bool,
    risk_high: int,
    risk_medium: int,
    interactive: bool
) -> None:
    """
    Запускает полный пайплайн анализа данных:

    1. Загрузка и валидация входного Excel-файла.
    2. Поиск периодов застоя (функция detect_stagnation).
    3. Генерация отчётов: CSV/Excel, графики динамики, summary.md.
    """
    if interactive:
        click.echo(message="=== Интерактивный режим ===")
        input = click.prompt(
            text='Путь к входному Excel-файлу',
            type=click.Path(exists=True, dir_okay=False, path_type=Path)
        )
        output = click.prompt(
            text='Директория для результатов',
            type=click.Path(file_okay=False, path_type=Path),
            default=Path('output')
        )
        min_days = click.prompt(
            text='Минимальная длительность застоя (дней)',
            type=int,
            default=28
        )
        top_n = click.prompt(
            text='Количество графиков для топ-кейсов',
            type=int,
            default=5
        )
        formats = click.prompt(
            text='Формат табличного отчёта (csv/excel/both)',
            type=click.Choice(
                choices=['csv', 'excel', 'both'], case_sensitive=False),
            default='csv'
        )
        comment_analysis = click.confirm(
            text='Анализировать комментарии на ключевые слова стагнации?',
            default=False
        )
        risk_high = click.prompt(
            text='Порог высокого риска (дней)',
            type=int,
            default=60
        )
        risk_medium = click.prompt(
            text='Порог среднего риска (дней)',
            type=int,
            default=42
        )
    elif input is None:
        raise click.UsageError(
            message="Не указан входной файл. Укажите --input или запустите в интерактивном режиме (--interactive)."
        )

    click.echo(message=f"Загрузка данных из {input}...")
    df_clean = load_data(filepath=input)

    click.echo(
        message=f"Анализ застоя (min_days={min_days}, risk_high={risk_high}, risk_medium={risk_medium})...")
    stagnation_df = detect_stagnation(
        df=df_clean,
        min_days=min_days,
        use_comment_analysis=comment_analysis,
        risk_high_days=risk_high,
        risk_medium_days=risk_medium
    )

    if not stagnation_df.empty:
        high_cnt = (stagnation_df['risk_level'] == 'high').sum()
        medium_cnt = (stagnation_df['risk_level'] == 'medium').sum()
        low_cnt = (stagnation_df['risk_level'] == 'low').sum()

        click.echo(message="\n Общая статистика")
        click.echo(message=f"Всего периодов застоя: {len(stagnation_df)}")
        click.echo(message=f"Высокий риск (≥{risk_high} дней): {high_cnt}")
        click.echo(
            message=f"Средний риск ({risk_medium}–{risk_high-1} дней): {medium_cnt}")
        click.echo(
            message=f"Низкий риск ({min_days}–{risk_medium-1} дней): {low_cnt}")
        click.echo(message="")
    else:
        click.echo(message="Застойных периодов не обнаружено.")

    export_formats = []
    if formats == 'both':
        export_formats = ['csv', 'excel']
    else:
        export_formats = [formats]

    click.echo(message=f"Генерация отчётов в {output}...")
    generate_all_reports(
        full_df=df_clean,
        stagnation_df=stagnation_df,
        output_dir=output,
        top_n_plots=top_n,
        formats=export_formats
    )

    click.echo(message="Готово!")


if __name__ == '__main__':
    analyze()
