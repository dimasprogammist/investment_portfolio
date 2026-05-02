
# ==================== ЦВЕТА И СТИЛИ ====================
# Светлая тема
COLORS = {
    'bg_main': '#d9d9d0',
    'bg_header': '#d9d9d0',
    'bg_card': '#ffffff',
    'accent': '#66bb6a',
    'accent_hover': '#8bc34a',
    'accent_light': '#e8f5e9',
    'text': '#424242',
    'text_secondary': '#757575',
    'text_light': '#9e9e9e',
    'success': '#7bc6cc',
    'danger': '#e57373',
    'warning': '#ffb74d',
    'info': '#64b5f6',
    'border': '#e0e0e0',
    'table_even': '#e0e0d8',
    'table_odd': '#f5f5f0',
    'table_header': '#d9d9d0',
    'table_selected': '#66bb6a',
}

# Тёмная тема
DARK_COLORS = {
    'bg_main': '#2d2d2d',
    'bg_header': '#2d2d2d',
    'bg_card': '#333333',
    'accent': '#4caf50',
    'accent_hover': '#66bb6a',
    'accent_light': '#2e7d32',
    'text': '#e0e0e0',
    'text_secondary': '#e0e0e0',#'#bdbdbd',
    'text_light': '#e0e0e0',#'#9e9e9e',
    'success': '#4db6ac',
    'danger': '#ef5350',
    'warning': '#ffa726',
    'info': '#42a5f5',
    'border': '#424242',
    'table_even': '#2d2d2d',
    'table_odd': '#333333',
    'table_header': '#2d2d2d',
    'table_selected': '#ef5350',
}

# Текущая тема
CURRENT_THEME = 'light'
#CURRENT_THEME = 'dark'

# ==================== ЦВЕТА ТИКЕРОВ ====================
TICKER_COLORS = {
    'SBER': '#2E8B57', 'ROSN': '#ffd500', 'YDEX': '#da0b0b', 'T': '#ffd500',
    'TATN': '#558e10', 'NVTK': '#9dd1ec', 'GMKN': '#1e5df1', 'X5': '#43df56',
    'MDMG': '#fed886', 'OZON': '#c7b3ff', 'ASTR': '#78877a', 'ELMT': '#fed886',
    'MAGN': '#1e5df1', 'NLMK': '#1e5df1', 'AQUA': '#78877a', 'FLOT': '#1e5df1',
    'POSI': '#da0b0b', 'PHOR': '#43df56', 'PLZL': '#ffd500', 'NMTP': '#1e5df1',
}

# ==================== ЦЕЛЕВЫЕ ДОЛИ ====================
TARGET_SHARES_STOCKS = {
    'SBER': 8.24, 'ROSN': 7.44, 'YDEX': 6.64, 'T': 5.44, 'TATN': 5.04, 'NVTK': 5.04,
    'GMKN': 4.24, 'X5': 4.24, 'MDMG': 4.24, 'OZON': 3.04, 'ASTR': 2.64, 'ELMT': 3.04,
    'MAGN': 2.64, 'NLMK': 2.64, 'AQUA': 2.64, 'FLOT': 2.64, 'POSI': 2.64, 'PHOR': 2.64,
    'PLZL': 2.64, 'NMTP': 2.24,
}

TARGET_SHARES_BONDS = {
    'SU26234RMFS3': 0.0, 'SU26248RMFS3': 3.67, 'SU26246RMFS7': 3.67, 'SU26242RMFS6': 3.66,
    'RU000A10ASC6': 1.5, 'RU000A10AUE8': 1.5, 'RU000A107W48': 1.5, 'RU000A10BFG2': 1.5,
    'RU000A10AXW4': 1.5, 'RU000A104XW2': 0.0, 'RU000A10CDZ5': 1.5,
}

# Объединяем для удобства
TARGET_SHARES = {**TARGET_SHARES_STOCKS, **TARGET_SHARES_BONDS}

# ==================== СПИСКИ ТИКЕРОВ ====================
STOCKS = ['SBER', 'ROSN', 'YDEX', 'T', 'TATN', 'NVTK', 'GMKN', 'X5',
          'MDMG', 'OZON', 'ASTR', 'ELMT', 'MAGN', 'NLMK', 'AQUA', 'FLOT',
          'POSI', 'PHOR', 'PLZL', 'NMTP']

BONDS = ['SU26234RMFS3', 'SU26248RMFS3', 'SU26246RMFS7', 'SU26242RMFS6',
         'RU000A10ASC6', 'RU000A10AUE8', 'RU000A107W48', 'RU000A10BFG2',
         'RU000A10AXW4', 'RU000A104XW2', 'RU000A10CDZ5']

# ==================== ВАЛЮТНЫЕ ОБЛИГАЦИИ ====================
CURRENCY_BONDS = {
    'RU000A10AXW4': 92.5,
}

CURRENCY_BONDS_CONFIG = {
    'RU000A10AXW4': {'currency': 'USD', 'nominal': 100},  # Сибур 0001P-03
}

# ==================== НАЗВАНИЯ КОМПАНИЙ ====================
TICKER_NAMES = {
    # Акции
    'SBER': 'Сбер',
    'ROSN': 'Роснефть',
    'YDEX': 'Яндекс',
    'T': 'Т-Банк',
    'TATN': 'Татнефть',
    'NVTK': 'Новатэк',
    'GMKN': 'Норникель',
    'X5': 'X5 Group',
    'MDMG': 'Мать и дитя',
    'OZON': 'Озон',
    'ASTR': 'Астра',
    'ELMT': 'Элемент',
    'MAGN': 'ММК',
    'NLMK': 'НЛМК',
    'AQUA': 'Инарктика',
    'FLOT': 'Совкомфлот',
    'POSI': 'Позитив',
    'PHOR': 'ФосАгро',
    'PLZL': 'Полюс',
    'NMTP': 'НМТП',
    # Облигации
    'SU26234RMFS3': 'ОФЗ 26234',
    'SU26248RMFS3': 'ОФЗ 26248',
    'SU26246RMFS7': 'ОФЗ 26246',
    'SU26242RMFS6': 'ОФЗ 26242',
    'RU000A10ASC6': 'Европлан 1P09',
    'RU000A10AUE8': 'РКД 001P-36R',
    'RU000A107W48': 'Инаркт 2P1',
    'RU000A10BFG2': 'Росатом 001H-05',
    'RU000A10AXW4': 'Сибур 0001P-03',
    'RU000A104XW2': 'Сибур 0001P-01',
    'RU000A10CDZ5': 'РКД 001P-45R',
}

# Тикер индекса для кэширования
INDEX_TICKER = 'MCFTR'


# Загрузка сохранённой темы
import json
import os

def load_theme():
    theme_file = os.path.join(os.path.dirname(__file__), '.theme')
    try:
        with open(theme_file, 'r') as f:
            data = json.load(f)
            return data.get('theme', 'light')
    except:
        return 'light'

# Применяем тему при импорте
CURRENT_THEME = load_theme()
if CURRENT_THEME == 'dark':
    COLORS = DARK_COLORS
