"""Конфигурация и допустимые значения для полей датасета."""

# Допустимые значения для доменов (domain)
ALLOWED_DOMAINS = {
    'Verbal_Request',
    'Listening',
    'Social',
    'Motor_Imitation'
}

# Допустимые значения для progress_flag (включая пустую строку)
ALLOWED_PROGRESS_FLAGS = {
    'improved',
    'stagnant',
    ''
}

# Маппинг для исправления опечаток в progress_flag
PROGRESS_FLAG_CORRECTIONS = {
    'импровед': 'improved',
    'improoved': 'improved',
    'stagnat': 'stagnant',
    'none': '',
    'nan': '',
    'нет': ''
}

# Допустимые типы специалистов
ALLOWED_SPECIALIST_TYPES = {
    'логопед',
    'дефектолог',
    'ПА',  # поведенческий аналитик
    'психолог',
    ''  # возможен пропуск
}

# Маппинг для исправления specialist_type
SPECIALIST_TYPE_CORRECTIONS = {
    'логопед': 'логопед',
    'дефектолог': 'дефектолог',
    'па': 'ПА',
    'поведенческий аналитик': 'ПА'
}

# Диапазон баллов
SCORE_MIN = 1
SCORE_MAX = 10

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