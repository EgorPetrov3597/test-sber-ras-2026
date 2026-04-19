"""Конфигурация и допустимые значения для полей датасета."""

# Допустимые домены (в нижнем регистре)
ALLOWED_DOMAINS = {
    'verbal_request',
    'listening',
    'social',
    'motor_imitation'
}

# Допустимые значения progress_flag (включая пустую строку)
ALLOWED_PROGRESS_FLAGS = {
    'improved',
    'stagnant',
    ''
}

# Маппинг для исправления опечаток в progress_flag
PROGRESS_FLAG_CORRECTIONS = {
    'импровед': 'improved',
    'improoved': 'improved',
    'stagnant': 'stagnant',
    'stagnat': 'stagnant',
    'none': '',
    'nan': '',
    'нет': ''
}

# Допустимые типы специалистов (в нижнем регистре)
ALLOWED_SPECIALIST_TYPES = {
    'логопед',
    'дефектолог',
    'па',
    'психолог',
    ''
}

# Маппинг для исправления specialist_type (ключи в нижнем регистре)
SPECIALIST_TYPE_CORRECTIONS = {
    'логопед': 'логопед',
    'дефектолог': 'дефектолог',
    'па': 'па',
    'поведенческий аналитик': 'па',
    'психолог': 'психолог'
}

# Диапазон баллов
SCORE_MIN = 1
SCORE_MAX = 10

# Пороги длительности для уровней риска (в днях)
RISK_HIGH_DAYS = 60
RISK_MEDIUM_DAYS = 42
# Всё, что >= RISK_MEDIUM_DAYS и < RISK_HIGH_DAYS — medium,
# от min_days до RISK_MEDIUM_DAYS — low.

STAGNATION_KEYWORDS = [
    'плато',
    'без изменений',
    'нет прогресса',
    'нет динамики',
    'стабильный уровень',
    'требуется смена',
    'нет расширения',
    'нет улучшения',
    'остановка',
    'застой'
]

# Обязательные колонки
REQUIRED_COLUMNS = [
    'child_id',
    'age',
    'diagnosis',
    'domain',
    'session_date',
    'assessment_score',
    'comment',
    'progress_flag',
    'specialist_type'
]
