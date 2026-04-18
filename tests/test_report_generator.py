from datetime import datetime

import pandas as pd
import pytest

from src.report_generator import (export_stagnation_report,
                                  generate_all_reports, generate_summary_md,
                                  plot_dynamics)


@pytest.fixture
def sample_stagnation_df():
    """Пример DataFrame с застоем."""
    data = {
        'child_id': ['СП01', 'СП02'],
        'domain': ['Verbal_Request', 'Listening'],
        'start_date': [datetime(year=2026, month=1, day=1), datetime(year=2026, month=2, day=1)],
        'end_date': [datetime(year=2026, month=2, day=1), datetime(year=2026, month=3, day=1)],
        'duration_days': [31, 28],
        'start_score': [3, 5],
        'end_score': [3, 5],
        'comments': ['Плато', 'Нет прогресса'],
        'risk_level': ['low', 'medium'],
    }
    return pd.DataFrame(data=data)


@pytest.fixture
def sample_full_df():
    """Полный DataFrame с сессиями."""
    data = {
        'child_id': ['СП01', 'СП01', 'СП02', 'СП02'],
        'domain': ['Verbal_Request', 'Verbal_Request', 'Listening', 'Listening'],
        'session_date': [
            datetime(year=2026, month=1, day=1), datetime(
                year=2026, month=2, day=1),
            datetime(year=2026, month=2, day=1), datetime(
                year=2026, month=3, day=1),
        ],
        'assessment_score': [3, 3, 5, 5],
        'comment': ['', '', '', ''],
    }
    return pd.DataFrame(data)


def test_export_stagnation_report_csv(sample_stagnation_df, tmp_path):
    """Проверяет сохранение CSV."""
    output = tmp_path / "report"
    export_stagnation_report(
        stagnation_df=sample_stagnation_df, output_path=output, formats=['csv'])
    csv_file = tmp_path / "report.csv"
    assert csv_file.exists()
    df_read = pd.read_csv(filepath_or_buffer=csv_file)
    assert len(df_read) == 2


def test_plot_dynamics(sample_full_df, tmp_path):
    """Проверяет создание графика."""
    plot_path = plot_dynamics(
        sample_full_df,
        child_id='СП01',
        domain='Verbal_Request',
        output_dir=tmp_path
    )
    assert plot_path is not None
    assert plot_path.exists()
    assert plot_path.suffix == '.png'


def test_generate_summary_md(sample_stagnation_df, tmp_path):
    """Проверяет создание markdown-файла."""
    md_path = tmp_path / "summary.md"
    generate_summary_md(stagnation_df=sample_stagnation_df,
                        output_path=md_path, top_n=2)
    assert md_path.exists()
    content = md_path.read_text(encoding='utf-8')
    assert 'СП01' in content
    assert 'Verbal_Request' in content


def test_generate_all_reports(sample_full_df, sample_stagnation_df, tmp_path):
    """Интеграционный тест генерации всех отчётов."""
    generate_all_reports(
        full_df=sample_full_df,
        stagnation_df=sample_stagnation_df,
        output_dir=tmp_path,
        top_n_plots=1,
        formats=['csv']
    )
    assert (tmp_path / "stagnation_report.csv").exists()
    assert (tmp_path / "summary.md").exists()
    plots_dir = tmp_path / "plots"
    assert plots_dir.exists()
    assert len(list(plots_dir.glob("*.png"))) >= 1
