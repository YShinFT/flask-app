from flask import Flask, render_template_string, request, jsonify, redirect, url_for, send_file, session
import json
import os
from datetime import datetime
import csv
import io
import random
from typing import Dict, List
import hashlib
import uuid
import os


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DATA_FILE = "finance_data.json"


def load_data():
    """Загрузка данных из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:  # Файл пустой
                    print("⚠️ Файл данных пустой, создаем новую структуру")
                    return create_default_data()

                data = json.loads(content)

                # Проверяем структуру данных
                if not isinstance(data, dict):
                    print("⚠️ Данные в неправильном формате, создаем новую структуру")
                    return create_default_data()

                # Проверяем наличие ключей
                if "users" not in data:
                    print("⚠️ В данных нет ключа 'users', восстанавливаем структуру")
                    default_data = create_default_data()
                    # Сохраняем существующие данные, но добавляем структуру users
                    if isinstance(data, dict):
                        data["users"] = default_data.get("users", [])
                        if "categories" not in data:
                            data["categories"] = default_data.get("categories", {})
                        if "investment_types" not in data:
                            data["investment_types"] = default_data.get("investment_types", [])
                        if "risk_profiles" not in data:
                            data["risk_profiles"] = default_data.get("risk_profiles", [])
                    return data

                return data

        except json.JSONDecodeError as e:
            print(f" Ошибка чтения JSON файла: {e}, создаем новую структуру")
            return create_default_data()
        except Exception as e:
            print(f"Неизвестная ошибка при загрузке данных: {e}, создаем новую структуру")
            return create_default_data()
    else:
        print(" Файл данных не существует, создаем новую структуру")
        return create_default_data()


def create_default_data():
    """Создание структуры данных по умолчанию с пользователями"""
    return {
        "users": [
            {
                "id": 1,
                "username": "demo",
                # Пароль "demo123" в хешированном виде
                "password_hash": "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090",
                "email": "demo@example.com",
                "created_at": "2024-01-01",
                "risk_profile": 2,  # умеренный профиль риска
                "transactions": [],  # Личные транзакции пользователя
                "investments": [],   # Личные инвестиции
                "goals": []          # Личные цели
            }
        ],
        # ОБЩИЕ ДАННЫЕ (для всех пользователей одинаковые):
        "categories": {
            "income": ["Зарплата", "Подработка", "Дивиденды", "Подарок", "Другое"],
            "expense": ["Еда", "Транспорт", "Аренда", "Развлечения", "Коммуналка", "Другое"]
        },
        "investment_types": ["Акции", "Облигации", "Депозиты", "Недвижимость", "ETF", "Криптовалюта"],
        "risk_profiles": [
            {"id": 1, "name": "Консервативный", "description": "Минимальный риск, стабильный доход", "stocks_ratio": 20, "bonds_ratio": 60, "cash_ratio": 20},
            {"id": 2, "name": "Умеренный", "description": "Баланс риска и доходности", "stocks_ratio": 50, "bonds_ratio": 40, "cash_ratio": 10},
            {"id": 3, "name": "Агрессивный", "description": "Высокий риск, потенциально высокая доходность", "stocks_ratio": 80, "bonds_ratio": 15, "cash_ratio": 5}
        ]
    }


def save_data(data):
    """Сохранение данных в файл"""
    # Гарантируем правильную структуру данных
    if not isinstance(data, dict):
        print(" Ошибка")
        return False

    # Гарантируем наличие обязательных ключей
    required_keys = ["users", "categories", "investment_types", "risk_profiles"]
    for key in required_keys:
        if key not in data:
            print(f"В данных отсутствует ключ '{key}', создаем...")
            default_data = create_default_data()
            data[key] = default_data.get(key)

    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f" Данные сохранены в {DATA_FILE}")
        return True
    except Exception as e:
        print(f" Ошибка при сохранении данных: {e}")
        return False


def get_base_html(title, content):
    """Базовый HTML шаблон с меню"""
    # Получаем текущего пользователя
    current_user = get_current_user()

    # Определяем активный пункт меню
    active_routes = {
        'Главная': '/',
        'Транзакции': '/transactions',
        'Инвестиции': '/investments',
        'Цели': '/goals',
        'Отчеты': '/reports',
        'Экспорт': '/export',
        'Сброс': '/reset-data'  # Добавили
    }

    # Иконки для меню
    icons = {
        'Главная': 'home',
        'Транзакции': 'exchange-alt',
        'Инвестиции': 'chart-line',
        'Цели': 'bullseye',
        'Отчеты': 'chart-pie',
        'Экспорт': 'download',
        'Сброс': 'trash-alt'  # Добавили
    }

    # Генерируем ссылки меню
    menu_links = ''

    if not current_user:
        # Если пользователь не авторизован - показываем только вход/регистрацию
        menu_links = '''
        <a href="/login" class="nav-link">
            <i class="fas fa-sign-in-alt"></i> Войти
        </a>
        <a href="/register" class="nav-link">
            <i class="fas fa-user-plus"></i> Регистрация
        </a>
        '''
        user_info = ''
    else:
        # Показываем полное меню для авторизованных
        for route_name, route_url in active_routes.items():
            is_active = "active" if title == route_name else ""
            icon = icons.get(route_name, 'circle')
            menu_links += f'''
            <a href="{route_url}" class="nav-link {is_active}">
                <i class="fas fa-{icon}"></i> {route_name}
            </a>
            '''

        # Добавляем кнопку выхода
        menu_links += f'''
        <a href="/logout" class="nav-link" style="color: #f44336;">
            <i class="fas fa-sign-out-alt"></i> Выйти
        </a>
        '''

        # Информация о пользователе
        user_info = f'''
        <div style="display: flex; align-items: center; gap: 10px; color: #666; margin-right: 20px;">
            <i class="fas fa-user-circle" style="font-size: 20px;"></i>
            <div>
                <div style="font-weight: 500; font-size: 14px;">{current_user['username']}</div>
                <div style="font-size: 11px; color: #999;">Пользователь</div>
            </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Финансовый менеджер</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}

            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}

            /* Навигационное меню */
            .navbar {{
                background: white;
                border-radius: 15px;
                padding: 15px 30px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap; 
                gap: 15px;
            }}

            .logo {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 24px;
                font-weight: bold;
                color: #333;
                text-decoration: none;
            }}

            .logo-icon {{
                font-size: 32px;
            }}

            .nav-links {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                justify-content: flex-end;
                flex-grow: 1;
            }}

            .nav-link {{
                text-decoration: none;
                color: #666;
                padding: 8px 16px;
                border-radius: 20px;
                transition: all 0.3s ease;
                font-weight: 500;
                font-size: 14px;
            }}

            .nav-link:hover {{
                background: #f0f0f0;
                color: #333;
            }}

            .nav-link.active {{
                background: #4CAF50;
                color: white;
            }}

            /* Основной контент */
            .content {{
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                min-height: 500px;
            }}

            /* Карточки */
            .card {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 25px;
                margin: 20px 0;
                border-left: 5px solid #4CAF50;
            }}

            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}

            .card-title {{
                font-size: 20px;
                color: #333;
                font-weight: 600;
            }}

            /* Формы */
            .form-group {{
                margin-bottom: 20px;
            }}

            label {{
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }}

            input, select, textarea {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border 0.3s ease;
            }}

            input:focus, select:focus, textarea:focus {{
                outline: none;
                border-color: #4CAF50;
            }}

            /* Кнопки */
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}

            .btn-primary {{
                background: #4CAF50;
                color: white;
                border: none;
            }}

            .btn-primary:hover {{
                background: #45a049;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.3);
            }}

            .btn-secondary {{
                background: #2196F3;
                color: white;
            }}

            .btn-danger {{
                background: #f44336;
                color: white;
            }}

            .btn-success {{
                background: #4CAF50;
                color: white;
            }}

            /* Таблицы */
            .table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}

            .table th {{
                background: #f5f5f5;
                padding: 15px;
                text-align: left;
                color: #333;
                font-weight: 600;
                border-bottom: 2px solid #e0e0e0;
            }}

            .table td {{
                padding: 15px;
                border-bottom: 1px solid #e0e0e0;
            }}

            .table tr:hover {{
                background: #f9f9f9;
            }}

            .income {{
                color: #4CAF50;
                font-weight: bold;
            }}

            .expense {{
                color: #f44336;
                font-weight: bold;
            }}

            /* Футер */
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: white;
                font-size: 14px;
            }}

            /* Адаптивность */
            @media (max-width: 768px) {{
                .navbar {{
                    flex-direction: column;
                    gap: 15px;
                }}

                .nav-links {{
                    flex-wrap: wrap;
                    justify-content: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Навигационная панель -->
            <nav class="navbar">
                <a href="/" class="logo">
                    <span class="logo-icon">💰</span>
                    ФинансМенеджер
                </a>

                <div style="display: flex; align-items: center; gap: 10px;">
                    {user_info}
                    <div class="nav-links">
                        {menu_links}
                    </div>
                </div>
            </nav>

            <!-- Основной контент -->
            <div class="content">
                {content}
            </div>

            <!-- Футер -->
            <div class="footer">
                <p>Финансовый менеджер | Яшин Владислав | {datetime.now().strftime('%Y')}</p>
            </div>
        </div>
    </body>
    </html>
    '''


# с пользоватеями

def get_current_user():
    """Получение текущего пользователя из сессии"""
    data = load_data()

    # Получаем ID пользователя из сессии
    user_id = session.get('user_id')
    if not user_id:
        return None

    # Ищем пользователя в данных
    for user in data.get("users", []):
        if user.get("id") == user_id:
            return user

    return None


def hash_password(password):
    """Хеширование пароля (для безопасного хранения)"""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username, password):
    """Проверка логина и пароля"""
    data = load_data()
    password_hash = hash_password(password)

    for user in data.get("users", []):
        if user.get("username") == username and user.get("password_hash") == password_hash:
            return user

    return None


def create_user(username, password, email=""):
    """Создание нового пользователя"""
    data = load_data()

    # Гарантируем, что ключ "users" существует
    if "users" not in data:
        data["users"] = []
        print("⚠️ Ключ 'users' не найден в данных, создаем пустой список")

    # Проверяем, не занято ли имя пользователя
    for user in data.get("users", []):
        if user.get("username") == username:
            return None  # Пользователь уже существует

    # Создаём нового пользователя
    new_user = {
        "id": len(data.get("users", [])) + 1,
        "username": username,
        "password_hash": hash_password(password),  # Храним только хеш!
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "risk_profile": 2,
        "transactions": [],  # Пустые списки для личных данных
        "investments": [],
        "goals": []
    }

    data["users"].append(new_user)
    save_data(data)

    print(f" Создан новый пользователь: {username} (ID: {new_user['id']})")
    return new_user


def load_user_data(user_id):
    """Загрузка данных конкретного пользователя"""
    data = load_data()

    # Ищем пользователя
    for user in data.get("users", []):
        if user.get("id") == user_id:
            # Возвращаем данные пользователя + общие настройки
            return {
                # Личные данные пользователя:
                "transactions": user.get("transactions", []),
                "investments": user.get("investments", []),
                "goals": user.get("goals", []),
                # Общие данные (для всех одинаковые):
                "categories": data.get("categories", {}),
                "investment_types": data.get("investment_types", []),
                "risk_profiles": data.get("risk_profiles", []),
                # Информация о пользователе:
                "user_info": {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "risk_profile": user.get("risk_profile", 2)
                }
            }

    return None


def save_user_data(user_id, user_data):
    """Сохранение данных пользователя"""
    # Загружаем ВСЕ данные из файла
    all_data = load_data()

    # Находим нужного пользователя
    for i, user in enumerate(all_data.get("users", [])):
        if user.get("id") == user_id:

            # Ключ "transactions", "investments", "goals" берем из user_data
            if "transactions" in user_data:
                all_data["users"][i]["transactions"] = user_data["transactions"]

            if "investments" in user_data:
                all_data["users"][i]["investments"] = user_data["investments"]

            if "goals" in user_data:
                all_data["users"][i]["goals"] = user_data["goals"]

            # Если есть информация о пользователе
            if "user_info" in user_data:
                all_data["users"][i]["risk_profile"] = user_data["user_info"].get("risk_profile", 2)

            # Сохраняем ВСЕ данные обратно в файл
            save_data(all_data)
            return True

    return False

def calculate_portfolio_value(investments):
    """Расчет общей стоимости портфеля"""
    total_value = 0
    if not isinstance(investments, list):
        return total_value

    for inv in investments:
        if isinstance(inv, dict):
            # Добавляем текущую стоимость или стоимость покупки
            current_value = inv.get("current_value")
            if current_value is not None:
                total_value += current_value
            else:
                total_value += inv.get("amount", 0)
    return total_value


def get_portfolio_allocation(investments):
    """Анализ распределения портфеля по типам активов"""
    allocation = {}
    if not isinstance(investments, list):
        return allocation

    total_value = calculate_portfolio_value(investments)
    if total_value == 0:
        return allocation

    for inv in investments:
        if isinstance(inv, dict):
            inv_type = inv.get("type", "Другое")
            current_value = inv.get("current_value", inv.get("amount", 0))

            if inv_type not in allocation:
                allocation[inv_type] = {"value": 0, "percentage": 0}

            allocation[inv_type]["value"] += current_value

    # Проценты
    for inv_type in allocation:
        allocation[inv_type]["percentage"] = (allocation[inv_type]["value"] / total_value) * 100

    return allocation


def generate_recommendations(investments, risk_profile_id=2):
    """Генерация рекомендаций по портфелю"""
    recommendations = []

    # Загружаем профили риска
    data = load_data()
    risk_profiles = data.get("risk_profiles", [])

    # Находим выбранный профиль риска
    selected_profile = None
    for profile in risk_profiles:
        if isinstance(profile, dict) and profile.get("id") == risk_profile_id:
            selected_profile = profile
            break

    if not selected_profile:
        selected_profile = risk_profiles[1] if len(risk_profiles) > 1 else {"name": "Умеренный", "stocks_ratio": 50,
                                                                            "bonds_ratio": 40, "cash_ratio": 10}

    # Анализ текущего портфеля
    allocation = get_portfolio_allocation(investments)
    total_value = calculate_portfolio_value(investments)

    if total_value == 0:
        recommendations.append({
            "type": "info",
            "title": "Начните инвестировать",
            "message": "Ваш портфель пуст. Начните с создания диверсифицированного портфеля.",
            "priority": "high"
        })
        return recommendations


    if len(allocation) < 3:
        recommendations.append({
            "type": "warning",
            "title": "Низкая диверсификация",
            "message": f"У вас всего {len(allocation)} типа активов. Рекомендуется не менее 3 для снижения рисков.",
            "priority": "medium"
        })

    # Проверка распределения по рискам
    stocks_value = allocation.get("Акции", {"value": 0})["value"] + allocation.get("ETF", {"value": 0})["value"]
    bonds_value = allocation.get("Облигации", {"value": 0})["value"]
    cash_value = allocation.get("Депозиты", {"value": 0})["value"]

    current_stocks_ratio = (stocks_value / total_value) * 100 if total_value > 0 else 0
    current_bonds_ratio = (bonds_value / total_value) * 100 if total_value > 0 else 0
    current_cash_ratio = (cash_value / total_value) * 100 if total_value > 0 else 0

    # Сравниваем с целевым распределением
    target_stocks = selected_profile.get("stocks_ratio", 50)
    target_bonds = selected_profile.get("bonds_ratio", 40)
    target_cash = selected_profile.get("cash_ratio", 10)

    if abs(current_stocks_ratio - target_stocks) > 15:
        action = "увеличьте" if current_stocks_ratio < target_stocks else "уменьшите"
        recommendations.append({
            "type": "advice",
            "title": "Баланс акций",
            "message": f"{action} долю акций с {current_stocks_ratio:.1f}% до {target_stocks}%",
            "priority": "medium"
        })

    if abs(current_bonds_ratio - target_bonds) > 15:
        action = "увеличьте" if current_bonds_ratio < target_bonds else "уменьшите"
        recommendations.append({
            "type": "advice",
            "title": "Баланс облигаций",
            "message": f"{action} долю облигаций с {current_bonds_ratio:.1f}% до {target_bonds}%",
            "priority": "medium"
        })

    # Рекомендации по пополнению
    if total_value < 50000:
        recommendations.append({
            "type": "info",
            "title": "Регулярные инвестиции",
            "message": "Рассмотрите возможность регулярных пополнений портфеля, даже небольшими суммами.",
            "priority": "low"
        })

    return recommendations[:3]


def calculate_goal_progress(goal):
    """Расчет прогресса цели"""
    if not isinstance(goal, dict):
        return 0

    saved = goal.get("saved", 0)
    target = goal.get("target", 1)  # чтобы избежать деления на 0

    if target <= 0:
        return 0

    progress = (saved / target) * 100
    return min(progress, 100)  # не более 100%


def get_goal_status(goal):
    """Определение статуса цели"""
    if not isinstance(goal, dict):
        return "unknown"

    progress = calculate_goal_progress(goal)
    deadline = goal.get("deadline", "")

    if progress >= 100:
        return "completed"

    try:
        deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
        today = datetime.now()
        days_left = (deadline_date - today).days

        if days_left < 0:
            return "overdue"
        elif days_left < 30:
            return "urgent"
        elif progress > 50:
            return "good_progress"
        else:
            return "active"
    except:
        return "active"


def get_monthly_summary(transactions):
    """Сводка по месяцам"""
    monthly_data = {}

    for t in transactions:
        if not isinstance(t, dict):
            continue

        date_str = t.get("date", "")
        if not date_str:
            continue

        try:
            # Извлекаем месяц и год
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month_key = date_obj.strftime('%Y-%m')
            month_name = date_obj.strftime('%B %Y')

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "name": month_name,
                    "income": 0,
                    "expense": 0,
                    "balance": 0,
                    "transactions": 0
                }

            amount = t.get("amount", 0)
            if amount > 0:
                monthly_data[month_key]["income"] += amount
            else:
                monthly_data[month_key]["expense"] += abs(amount)

            monthly_data[month_key]["balance"] += amount
            monthly_data[month_key]["transactions"] += 1

        except:
            continue

    # Сортируем по дате (новые месяцы сверху)
    sorted_months = sorted(
        monthly_data.items(),
        key=lambda x: x[0],
        reverse=True
    )

    return dict(sorted_months[:6])  # Последние 6 месяцев


def get_category_summary(transactions, trans_type="expense"):
    """Сводка по категориям"""
    category_data = {}

    for t in transactions:
        if not isinstance(t, dict):
            continue

        # Фильтруем по типу (доход или расход)
        if trans_type == "expense" and t.get("amount", 0) >= 0:
            continue
        if trans_type == "income" and t.get("amount", 0) < 0:
            continue

        category = t.get("category", "Другое")
        amount = abs(t.get("amount", 0))

        if category not in category_data:
            category_data[category] = {
                "amount": 0,
                "count": 0,
                "percentage": 0
            }

        category_data[category]["amount"] += amount
        category_data[category]["count"] += 1

    # Сортируем по сумме (большие сверху)
    sorted_categories = sorted(
        category_data.items(),
        key=lambda x: x[1]["amount"],
        reverse=True
    )

    # Рассчитываем проценты
    total = sum(data["amount"] for _, data in sorted_categories)
    result = {}

    for category, data in sorted_categories[:8]:  # Топ 8 категорий
        data["percentage"] = (data["amount"] / total * 100) if total > 0 else 0
        result[category] = data

    return result


def get_investment_summary(investments):
    """Сводка по инвестициям"""
    summary = {
        "total_value": 0,
        "total_invested": 0,
        "total_profit": 0,
        "profit_percentage": 0,
        "by_type": {}
    }

    for inv in investments:
        if not isinstance(inv, dict):
            continue

        inv_type = inv.get("type", "Другое")
        current_value = inv.get("current_value", inv.get("amount", 0))
        purchase_value = inv.get("amount", 0)
        profit = current_value - purchase_value

        summary["total_value"] += current_value
        summary["total_invested"] += purchase_value
        summary["total_profit"] += profit

        if inv_type not in summary["by_type"]:
            summary["by_type"][inv_type] = {
                "value": 0,
                "count": 0,
                "profit": 0
            }

        summary["by_type"][inv_type]["value"] += current_value
        summary["by_type"][inv_type]["count"] += 1
        summary["by_type"][inv_type]["profit"] += profit

    if summary["total_invested"] > 0:
        summary["profit_percentage"] = (summary["total_profit"] / summary["total_invested"] * 100)

    return summary


# АВТОРИЗАЦИЯ
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Страница входа"""
    # Если пользователь уже авторизован - перенаправляем на главную
    if get_current_user():
        return redirect('/')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = authenticate_user(username, password)

        if user:
            # Сохраняем пользователя в сессии
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            return '''
            <script>
                alert("Неверное имя пользователя или пароль");
                window.location.href = "/login";
            </script>
            '''

    # GET запрос - показываем форму
    content = '''
    <div style="max-width: 400px; margin: 50px auto; padding: 0 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">💰</div>
            <h1 style="color: #333; margin-bottom: 10px;">Вход в систему</h1>
            <p style="color: #666;">Войдите в свой аккаунт</p>
        </div>

        <div class="card" style="padding: 30px;">
            <form action="/login" method="POST">
                <div class="form-group">
                    <label for="username">Имя пользователя</label>
                    <input type="text" id="username" name="username" required 
                           placeholder="demo" 
                           style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="password">Пароль</label>
                    <input type="password" id="password" name="password" required 
                           placeholder="demo123" 
                           style="width: 100%; padding: 12px;">
                </div>

                <button type="submit" class="btn btn-primary" 
                        style="width: 100%; padding: 12px; margin-top: 20px;">
                    <i class="fas fa-sign-in-alt"></i> Войти
                </button>
            </form>

            <div style="text-align: center; margin-top: 20px;">
                <p style="color: #666; margin-bottom: 10px;">Нет аккаунта?</p>
                <a href="/register" class="btn" 
                   style="background: #f0f0f0; color: #333; padding: 10px 20px;">
                    <i class="fas fa-user-plus"></i> Зарегистрироваться
                </a>
            </div>
        </div>

        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 14px;">
            <p><strong>Демо доступ:</strong></p>
            <p>Имя пользователя: <strong>demo</strong></p>
            <p>Пароль: <strong>demo123</strong></p>
        </div>
    </div>
    '''

    return get_base_html("Вход", content)


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    """Страница регистрации"""
    # Если пользователь уже авторизован - перенаправляем
    if get_current_user():
        return redirect('/')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()

        # Простая валидация
        if len(username) < 3:
            return '''
            <script>
                alert("Имя пользователя должно быть не менее 3 символов");
                window.location.href = "/register";
            </script>
            '''

        if len(password) < 4:
            return '''
            <script>
                alert("Пароль должен быть не менее 4 символов");
                window.location.href = "/register";
            </script>
            '''

        user = create_user(username, password, email)

        if user:
            # Автоматически входим после регистрации
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            return '''
            <script>
                alert("Пользователь с таким именем уже существует");
                window.location.href = "/register";
            </script>
            '''

    content = '''
    <div style="max-width: 400px; margin: 50px auto; padding: 0 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 64px; margin-bottom: 20px;">💰</div>
            <h1 style="color: #333; margin-bottom: 10px;">Регистрация</h1>
            <p style="color: #666;">Создайте новый аккаунт</p>
        </div>

        <div class="card" style="padding: 30px;">
            <form action="/register" method="POST">
                <div class="form-group">
                    <label for="username">Имя пользователя *</label>
                    <input type="text" id="username" name="username" required 
                           placeholder="Придумайте имя (мин. 3 символа)" 
                           style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="email">Email (необязательно)</label>
                    <input type="email" id="email" name="email" 
                           placeholder="example@mail.com" 
                           style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="password">Пароль *</label>
                    <input type="password" id="password" name="password" required 
                           placeholder="Придумайте пароль (мин. 4 символа)" 
                           style="width: 100%; padding: 12px;">
                </div>

                <button type="submit" class="btn btn-primary" 
                        style="width: 100%; padding: 12px; margin-top: 20px;">
                    <i class="fas fa-user-plus"></i> Зарегистрироваться
                </button>
            </form>

            <div style="text-align: center; margin-top: 20px;">
                <p style="color: #666; margin-bottom: 10px;">Уже есть аккаунт?</p>
                <a href="/login" class="btn" 
                   style="background: #f0f0f0; color: #333; padding: 10px 20px;">
                    <i class="fas fa-sign-in-alt"></i> Войти
                </a>
            </div>
        </div>
    </div>
    '''

    return get_base_html("Регистрация", content)


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()  # Очищаем все данные сессии
    return redirect('/login')
#  ГЛАВНАЯ СТРАНИЦА
@app.route('/')
def index():
    # проверка авторизации
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')
    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    # Безопасно получаем данные
    transactions = user_data.get("transactions", [])
    incomes = [t for t in transactions if isinstance(t, dict) and t.get("type") == "income"]
    expenses = [t for t in transactions if isinstance(t, dict) and t.get("type") == "expense"]

    total_income = sum(t.get("amount", 0) for t in incomes if isinstance(t.get("amount"), (int, float)))
    total_expense = sum(abs(t.get("amount", 0)) for t in expenses if isinstance(t.get("amount"), (int, float)))
    balance = total_income - total_expense

    # Последние транзакции
    recent_transactions = transactions[-5:] if len(transactions) > 5 else transactions

    # Секция инвестиций (добавляем данные для главной страницы)
    investments = user_data.get("investments", [])
    recent_investments = investments[-3:] if len(investments) > 3 else investments
    total_investment = calculate_portfolio_value(investments)

    investments_html = ""
    for inv in recent_investments:
        if isinstance(inv, dict):
            current_value = inv.get("current_value", inv.get("amount", 0))
            purchase_value = inv.get("amount", 0)
            profit = current_value - purchase_value
            profit_percent = (profit / purchase_value * 100) if purchase_value > 0 else 0

            profit_class = "income" if profit >= 0 else "expense"
            profit_sign = "+" if profit >= 0 else ""

            investments_html += f'''
               <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #e0e0e0;">
                   <div>
                       <div style="font-weight: 500;">{inv.get('name', 'Без названия')}</div>
                       <div style="font-size: 12px; color: #666;">{inv.get('type', 'Акции')} • {inv.get('purchase_date', 'Нет даты')}</div>
                   </div>
                   <div>
                       <div style="font-weight: bold; text-align: right;">{current_value:,.0f} ₽</div>
                       <div style="font-size: 12px; color: {'#4CAF50' if profit >= 0 else '#f44336'}; text-align: right;">
                           {profit_sign}{profit:,.0f} ₽ ({profit_percent:+.1f}%)
                       </div>
                   </div>
               </div>
               '''

    if not investments_html:
        investments_html = '<p style="text-align: center; color: #666; padding: 20px;">Нет инвестиций</p>'
    content = f'''
    <h1 <h1 style="color: #333; margin-bottom: 30px;">
        Добро пожаловать, {current_user['username']}!</h1>

    <!-- Карточки статистики -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #2196F3;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Текущий баланс</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #2196F3;">{balance:,.2f} ₽</div>
            <p>Общая сумма средств</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #4CAF50;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Всего доходов</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #4CAF50;">+{total_income:,.2f} ₽</div>
            <p>Сумма всех поступлений</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #f44336;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Всего расходов</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #f44336;">-{total_expense:,.2f} ₽</div>
            <p>Сумма всех трат</p>
        </div>
    </div>

    <!-- Быстрые действия -->
    <div style="background: #f8f9fa; border-radius: 10px; padding: 25px; margin: 20px 0; border-left: 5px solid #4CAF50;">
        <h2 style="font-size: 20px; color: #333; margin-bottom: 20px;">Быстрые действия</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <a href="/add-transaction?type=income" class="btn btn-primary" style="padding: 12px; text-align: center;">
                <i class="fas fa-plus-circle"></i> Добавить доход
            </a>
            <a href="/add-transaction?type=expense" class="btn btn-danger" style="padding: 12px; text-align: center;">
                <i class="fas fa-minus-circle"></i> Добавить расход
            </a>
            <a href="/investments" class="btn btn-secondary" style="padding: 12px; text-align: center;">
                <i class="fas fa-chart-line"></i> Инвестиции
            </a>
            <a href="/goals" class="btn btn-success" style="padding: 12px; text-align: center;">
                <i class="fas fa-bullseye"></i> Цели
            </a>
        </div>
    </div>

    <!-- Последние транзакции -->
    <div style="background: #f8f9fa; border-radius: 10px; padding: 25px; margin: 20px 0; border-left: 5px solid #4CAF50;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="font-size: 20px; color: #333;">Последние операции</h2>
            <a href="/transactions" class="btn btn-primary" style="padding: 8px 16px;">Все операции</a>
        </div>

        {get_recent_transactions_table(recent_transactions)}
    </div>
    '''

    return get_base_html("Главная", content)


def get_recent_transactions_table(transactions):
    if not transactions:
        return '<p style="text-align: center; color: #666; padding: 20px;">Нет операций</p>'

    rows = ''
    for t in transactions:
        if not isinstance(t, dict):
            continue

        amount = t.get("amount", 0)
        sign = "+" if amount > 0 else ""

        rows += f'''
        <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #e0e0e0;">
            <div>
                <div style="font-weight: 500;">{t.get('description', 'Без описания')}</div>
                <div style="font-size: 12px; color: #666;">{t.get('date', 'Нет даты')} • {t.get('category', 'Другое')}</div>
            </div>
            <div style="font-weight: bold; color: {'#4CAF50' if amount > 0 else '#f44336'}">
                {sign}{abs(amount):,.2f} ₽
            </div>
        </div>
        '''

    return f'''
    <div>
        {rows}
    </div>
    '''


# ДОБАВЛЕНИЕ ТРАНЗАКЦИИ
@app.route('/add-transaction')
def add_transaction_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    trans_type = request.args.get('type', 'income')

    # Безопасно получаем категории
    categories_data = user_data.get("categories", {})
    if isinstance(categories_data, dict):
        categories = categories_data.get(trans_type, [])
    else:
        categories = ["Зарплата", "Еда", "Транспорт", "Другое"]

    content = f'''
    <h1 style="color: #333; margin-bottom: 20px;">Добавить {'доход' if trans_type == 'income' else 'расход'}</h1>

    <div class="card">
        <form action="/api/add-transaction" method="POST">
            <input type="hidden" name="type" value="{trans_type}">

            <div class="form-group">
                <label for="amount">Сумма (₽)</label>
                <input type="number" id="amount" name="amount" step="0.01" min="0.01" required 
                       placeholder="Введите сумму" style="width: 100%; padding: 10px;">
            </div>

            <div class="form-group">
                <label for="description">Описание</label>
                <input type="text" id="description" name="description" required 
                       placeholder="Например: Зарплата за январь" style="width: 100%; padding: 10px;">
            </div>

            <div class="form-group">
                <label for="category">Категория</label>
                <select id="category" name="category" required style="width: 100%; padding: 10px;">
                    <option value="">Выберите категорию</option>
                    {''.join([f'<option value="{cat}">{cat}</option>' for cat in categories])}
                </select>
            </div>

            <div class="form-group">
                <label for="date">Дата</label>
                <input type="date" id="date" name="date" value="{datetime.now().strftime('%Y-%m-%d')}" 
                       required style="width: 100%; padding: 10px;">
            </div>

            <div style="display: flex; gap: 10px; margin-top: 30px;">
                <button type="submit" class="btn {'btn-primary' if trans_type == 'income' else 'btn-danger'}" 
                        style="padding: 10px 20px;">
                    <i class="fas fa-save"></i> Сохранить {'доход' if trans_type == 'income' else 'расход'}
                </button>
                <a href="/transactions" class="btn" style="background: #f0f0f0; padding: 10px 20px;">Отмена</a>
            </div>
        </form>
    </div>
    '''

    return get_base_html(f"Добавить {'доход' if trans_type == 'income' else 'расход'}", content)


# API для добавления транзакции
@app.route('/api/add-transaction', methods=['POST'])
def api_add_transaction():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        amount = float(request.form.get("amount", 0))
        trans_type = request.form.get("type", "income")

        # Если это расход, делаем отрицательным
        if trans_type == "expense":
            amount = -abs(amount)

        transaction = {
            "id": len(user_data.get("transactions", [])) + 1,
            "date": request.form.get("date", datetime.now().strftime("%Y-%m-%d")),
            "type": trans_type,
            "amount": amount,
            "description": request.form.get("description", ""),
            "category": request.form.get("category", "Другое")
        }

        # Инициализируем список транзакций, если его нет
        if "transactions" not in user_data:
            user_data["transactions"] = []

        user_data["transactions"].append(transaction)
        save_user_data(current_user['id'], user_data)

        return redirect("/transactions")

    except Exception as e:
        print(f"Ошибка при добавлении транзакции: {e}")
        return redirect("/add-transaction?type=" + request.form.get("type", "income"))


# ТРАНЗАКЦИИ
@app.route('/transactions')
def transactions_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    transactions = user_data.get("transactions", [])

    # Сортируем транзакции по дате (новые сверху)
    try:
        transactions_sorted = sorted(
            [t for t in transactions if isinstance(t, dict) and t.get('date')],
            key=lambda x: x.get('date', ''),
            reverse=True
        )
    except:
        transactions_sorted = transactions

    content = f'''
    <div class="card-header">
        <h1 class="card-title" style="font-size: 28px;">История транзакций</h1>
        <div>
            <a href="/add-transaction?type=income" class="btn btn-primary" style="padding: 10px 20px;">
                <i class="fas fa-plus"></i> Добавить доход
            </a>
            <a href="/add-transaction?type=expense" class="btn btn-danger" style="padding: 10px 20px; margin-left: 10px;">
                <i class="fas fa-minus"></i> Добавить расход
            </a>
        </div>
    </div>

    <div style="display: flex; gap: 20px; margin: 20px 0;">
        <div class="btn" style="background: #f0f0f0; padding: 8px 16px;">Все: {len(transactions)}</div>
        <div class="btn" style="background: #e8f5e9; color: #4CAF50; padding: 8px 16px;">
            Доходы: {len([t for t in transactions if isinstance(t, dict) and t.get("type") == "income"])}
        </div>
        <div class="btn" style="background: #ffebee; color: #f44336; padding: 8px 16px;">
            Расходы: {len([t for t in transactions if isinstance(t, dict) and t.get("type") == "expense"])}
        </div>
    </div>

    {get_transactions_table(transactions_sorted)}
    '''

    return get_base_html("Транзакции", content)


def get_transactions_table(transactions):
    if not transactions:
        return '''
        <div style="text-align: center; padding: 50px; color: #666;">
            <i class="fas fa-exchange-alt" style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;"></i>
            <p style="font-size: 18px;">Нет операций</p>
            <p style="margin-top: 10px;">Добавьте первую транзакцию, чтобы начать учет финансов!</p>
            <div style="margin-top: 20px;">
                <a href="/add-transaction?type=income" class="btn btn-primary" style="margin-right: 10px;">
                    <i class="fas fa-plus"></i> Добавить доход
                </a>
                <a href="/add-transaction?type=expense" class="btn btn-danger">
                    <i class="fas fa-minus"></i> Добавить расход
                </a>
            </div>
        </div>
        '''

    rows = ''
    for t in transactions:
        if not isinstance(t, dict):
            continue

        amount = t.get("amount", 0)
        row_class = "income" if amount > 0 else "expense"
        sign = "+" if amount > 0 else ""

        # Форматируем дату для отображения
        date_str = t.get('date', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            display_date = date_obj.strftime('%d.%m.%Y')
        except:
            display_date = date_str

        rows += f'''
        <tr>
            <td>{display_date}</td>
            <td>{t.get('description', 'Без описания')}</td>
            <td>{t.get('category', 'Другое')}</td>
            <td class="{row_class}">{sign}{abs(amount):,.2f} ₽</td>
        </tr>
        '''

    return f'''
    <div style="overflow-x: auto;">
        <table class="table">
            <thead>
                <tr>
                    <th>Дата</th>
                    <th>Описание</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    '''


#ЭКСПОРТ
@app.route('/export')
def export_page():
    content = '''
    <h1 style="color: #333; margin-bottom: 30px;">Экспорт данных</h1>

    <div class="card">
        <h3 style="margin-bottom: 20px;"> Экспорт в различные форматы</h3>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
            <div style="text-align: center; padding: 25px; background: #e8f5e9; border-radius: 10px;">
                <i class="fas fa-file-csv" style="font-size: 48px; color: #4CAF50; margin-bottom: 15px;"></i>
                <h4>CSV формат</h4>
                <p style="color: #666; margin: 10px 0;">Для Excel и таблиц</p>
                <a href="/api/export/csv" class="btn btn-primary" style="padding: 10px 20px;">
                    <i class="fas fa-download"></i> Скачать CSV
                </a>
            </div>

            <div style="text-align: center; padding: 25px; background: #fff3e0; border-radius: 10px;">
                <i class="fas fa-file-alt" style="font-size: 48px; color: #FF9800; margin-bottom: 15px;"></i>
                <h4>JSON формат</h4>
                <p style="color: #666; margin: 10px 0;">Для резервного копирования</p>
                <a href="/api/export/json" class="btn btn-primary" style="padding: 10px 20px;">
                    <i class="fas fa-download"></i> Скачать JSON
                </a>
            </div>

            <div style="text-align: center; padding: 25px; background: #e3f2fd; border-radius: 10px;">
                <i class="fas fa-print" style="font-size: 48px; color: #2196F3; margin-bottom: 15px;"></i>
                <h4>Печатная версия</h4>
                <p style="color: #666; margin: 10px 0;">Для распечатки отчета</p>
                <button onclick="window.print()" class="btn btn-primary" style="padding: 10px 20px;">
                    <i class="fas fa-print"></i> Печать отчета
                </button>
            </div>
        </div>

        <div class="card" style="margin-top: 30px; background: #fffde7; padding: 20px;">
            <h4 style="color: #FF9800; margin-bottom: 15px;">
                <i class="fas fa-exclamation-triangle"></i> Важная информация
            </h4>
            <ul style="padding-left: 20px; color: #666;">
                <li style="margin-bottom: 10px;"> Данные экспортируются в текущем состоянии</li>
                <li style="margin-bottom: 10px;"> Pекомендуется регулярно делать резервные копии</li>
                <li style="margin-bottom: 10px;"> Экспортированные файлы содержат все транзакции</li>
                <li style="margin-bottom: 10px;"> Ваши данные хранятся локально</li>
            </ul>
        </div>
    </div>
    '''

    return get_base_html("Экспорт", content)


# API для экспорта CSV
@app.route('/api/export/csv')
def export_csv():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Заголовок для транзакций
    writer.writerow(["ТРАНЗАКЦИИ"])
    writer.writerow(["ID", "Дата", "Тип", "Категория", "Сумма (₽)", "Описание"])

    transactions = user_data.get("transactions", [])
    for t in transactions:
        if not isinstance(t, dict):
            continue

        writer.writerow([
            t.get("id", ""),
            t.get("date", ""),
            "Доход" if t.get("type") == "income" else "Расход",
            t.get("category", ""),
            t.get("amount", 0),
            t.get("description", "")
        ])

    # Возвращаем CSV файл
    output.seek(0)

    # Создаем ответ
    response = send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='finance_export.csv'
    )

    return response


# API для экспорта JSON
@app.route('/api/export/json')
def export_json():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    # Создаем JSON в памяти
    json_data = json.dumps(user_data, ensure_ascii=False, indent=2)

    # Создаем ответ
    response = send_file(
        io.BytesIO(json_data.encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name='finance_export.json'
    )

    return response


# инвестиции
@app.route('/investments')
def investments_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    investments = user_data.get("investments", [])

    # Расчет статистики
    total_value = calculate_portfolio_value(investments)
    allocation = get_portfolio_allocation(investments)
    recommendations = generate_recommendations(investments)

    # Генерация HTML для распределения активов
    allocation_html = ""
    for inv_type, stats in allocation.items():
        percentage = stats["percentage"]
        color = "#4CAF50" if percentage > 20 else "#2196F3" if percentage > 10 else "#FF9800"

        allocation_html += f'''
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>{inv_type}</span>
                <span><strong>{percentage:.1f}%</strong> ({stats["value"]:,.0f} ₽)</span>
            </div>
            <div style="height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden;">
                <div style="width: {percentage}%; height: 100%; background: {color}; border-radius: 5px;"></div>
            </div>
        </div>
        '''

    if not allocation_html:
        allocation_html = '<p style="text-align: center; color: #666;">Нет активов в портфеле</p>'

    # Генерация HTML для рекомендаций
    recommendations_html = ""
    for i, rec in enumerate(recommendations):
        icon = "💡" if rec["type"] == "advice" else "⚠️" if rec["type"] == "warning" else "ℹ️"
        color = "#4CAF50" if rec["priority"] == "low" else "#FF9800" if rec["priority"] == "medium" else "#f44336"

        recommendations_html += f'''
        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {color};">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span style="font-size: 20px;">{icon}</span>
                <strong>{rec["title"]}</strong>
            </div>
            <p style="margin: 0; color: #555;">{rec["message"]}</p>
        </div>
        '''

    if not recommendations_html:
        recommendations_html = '<p style="text-align: center; color: #666;">Нет рекомендаций. Портфель сбалансирован!</p>'

    # Генерация таблицы инвестиций
    investments_html = ""
    for inv in investments:
        if isinstance(inv, dict):
            purchase_date = inv.get("purchase_date", "")
            try:
                date_obj = datetime.strptime(purchase_date, '%Y-%m-%d')
                display_date = date_obj.strftime('%d.%m.%Y')
            except:
                display_date = purchase_date

            current_value = inv.get("current_value", inv.get("amount", 0))
            purchase_value = inv.get("amount", 0)
            profit = current_value - purchase_value
            profit_percent = (profit / purchase_value * 100) if purchase_value > 0 else 0

            profit_class = "income" if profit >= 0 else "expense"
            profit_sign = "+" if profit >= 0 else ""

            investments_html += f'''
            <tr>
                <td><strong>{inv.get("name", "")}</strong></td>
                <td>{inv.get("type", "Акции")}</td>
                <td>{display_date}</td>
                <td>{purchase_value:,.0f} ₽</td>
                <td>{current_value:,.0f} ₽</td>
                <td class="{profit_class}">{profit_sign}{profit:,.0f} ₽ ({profit_percent:+.1f}%)</td>
            </tr>
            '''

    if not investments_html:
        investments_html = '''
        <tr>
            <td colspan="6" style="text-align: center; padding: 40px; color: #666;">
                <i class="fas fa-chart-line" style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;"></i>
                <p style="font-size: 18px;">Портфель пуст</p>
                <p style="margin-top: 10px;">Добавьте первый актив в портфель!</p>
            </td>
        </tr>
        '''

    content = f'''
    <div class="card-header">
        <h1 class="card-title" style="font-size: 28px;">Инвестиционный портфель</h1>
        <div>
            <a href="/add-investment" class="btn btn-primary" style="padding: 10px 20px;">
                <i class="fas fa-plus"></i> Добавить актив
            </a>
            <a href="/investment-reports" class="btn btn-secondary" style="padding: 10px 20px; margin-left: 10px;">
                <i class="fas fa-chart-pie"></i> Аналитика
            </a>
        </div>
    </div>

    <!-- Общая статистика -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #2196F3;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Общая стоимость</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #2196F3;">{total_value:,.0f} ₽</div>
            <p>Стоимость портфеля</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #4CAF50;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Активов в портфеле</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #4CAF50;">{len(investments)}</div>
            <p>Количество активов</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #FF9800;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Типов активов</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #FF9800;">{len(allocation)}</div>
            <p>Диверсификация</p>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin: 30px 0;">
        <!-- Левая колонка: Распределение активов -->
        <div class="card">
            <h3 style="margin-bottom: 20px; color: #333;">
                <i class="fas fa-chart-pie"></i> Распределение активов
            </h3>
            {allocation_html}
        </div>

        <!-- Правая колонка: Рекомендации -->
        <div class="card">
            <h3 style="margin-bottom: 20px; color: #333;">
                <i class="fas fa-lightbulb"></i> Рекомендации
            </h3>
            {recommendations_html}

            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                <h4 style="color: #666; margin-bottom: 10px;">Советы по диверсификации:</h4>
                <ul style="padding-left: 20px; color: #555;">
                    <li style="margin-bottom: 8px;"> Распределяйте средства между разными типами активов</li>
                    <li style="margin-bottom: 8px;"> Регулярно пересматривайте портфель (ребалансировка)</li>
                    <li style="margin-bottom: 8px;"> Инвестируйте в соответствии с вашим профилем риска</li>
                    <li> Не забывайте про "подушку безопасности" в виде депозитов</li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Таблица инвестиций -->
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="color: #333;">
                <i class="fas fa-list"></i> Список активов
            </h3>
            <a href="/add-investment" class="btn btn-primary" style="padding: 8px 16px;">
                <i class="fas fa-plus"></i> Добавить новый актив
            </a>
        </div>

        <div style="overflow-x: auto;">
            <table class="table">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Тип</th>
                        <th>Дата покупки</th>
                        <th>Стоимость покупки</th>
                        <th>Текущая стоимость</th>
                        <th>Прибыль</th>
                    </tr>
                </thead>
                <tbody>
                    {investments_html}
                </tbody>
            </table>
        </div>
    </div>
    '''

    return get_base_html("Инвестиции", content)


@app.route('/add-investment')
def add_investment_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    investment_types = user_data.get("investment_types", ["Акции", "Облигации", "Депозиты", "Недвижимость"])

    content = f'''
     <h1 style="color: #333; margin-bottom: 20px;">Добавить актив в портфель</h1>

     <div class="card">
         <form action="/api/add-investment" method="POST">
             <div class="form-group">
                 <label for="name">Название актива</label>
                 <input type="text" id="name" name="name" required 
                        placeholder="Например: Акции Газпром, Облигации РФ, Депозит в Сбербанке" 
                        style="width: 100%; padding: 12px;">
             </div>

             <div class="form-group">
                 <label for="type">Тип актива</label>
                 <select id="type" name="type" required style="width: 100%; padding: 12px;">
                     <option value="">Выберите тип актива</option>
                     {''.join([f'<option value="{t}">{t}</option>' for t in investment_types])}
                 </select>
             </div>

             <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                 <div class="form-group">
                     <label for="amount">Сумма инвестиции (₽)</label>
                     <input type="number" id="amount" name="amount" step="0.01" min="0.01" required 
                            placeholder="10000" style="width: 100%; padding: 12px;">
                 </div>

                 <div class="form-group">
                     <label for="current_value">Текущая стоимость (₽)</label>
                     <input type="number" id="current_value" name="current_value" step="0.01" min="0.01" 
                            placeholder="Оставьте пустым, если равна сумме инвестиции" 
                            style="width: 100%; padding: 12px;">
                 </div>
             </div>

             <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                 <div class="form-group">
                     <label for="purchase_date">Дата покупки</label>
                     <input type="date" id="purchase_date" name="purchase_date" 
                            value="{datetime.now().strftime('%Y-%m-%d')}" 
                            required style="width: 100%; padding: 12px;">
                 </div>

                 <div class="form-group">
                     <label for="expected_return">Ожидаемая доходность (% годовых)</label>
                     <input type="number" id="expected_return" name="expected_return" step="0.1" 
                            placeholder="Например: 10" style="width: 100%; padding: 12px;">
                 </div>
             </div>

             <div class="form-group">
                 <label for="notes">Примечания (необязательно)</label>
                 <textarea id="notes" name="notes" rows="3" 
                           placeholder="Дополнительная информация: тикер, эмитент, условия и т.д." 
                           style="width: 100%; padding: 12px; resize: vertical;"></textarea>
             </div>

             <div style="display: flex; gap: 10px; margin-top: 30px;">
                 <button type="submit" class="btn btn-primary" style="padding: 12px 24px;">
                     <i class="fas fa-save"></i> Добавить актив
                 </button>
                 <a href="/investments" class="btn" style="background: #f0f0f0; padding: 12px 24px;">Отмена</a>
             </div>
         </form>
     </div>
     '''

    return get_base_html("Добавить инвестицию", content)

# добавление инвестиций
@app.route('/api/add-investment', methods=['POST'])
def api_add_investment():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        amount = float(request.form.get("amount", 0))
        current_value_str = request.form.get("current_value", "").strip()

        # Если текущая стоимость не указана, используем сумму инвестиции
        if current_value_str:
            current_value = float(current_value_str)
        else:
            current_value = amount

        investment = {
            "id": len(user_data.get("investments", [])) + 1,
            "name": request.form.get("name", ""),
            "type": request.form.get("type", "Акции"),
            "amount": amount,
            "current_value": current_value,
            "purchase_date": request.form.get("purchase_date", datetime.now().strftime("%Y-%m-%d")),
            "expected_return": request.form.get("expected_return"),
            "notes": request.form.get("notes", ""),
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }

        # Инициализируем список инвестиций, если его нет
        if "investments" not in user_data:
            user_data["investments"] = []

        user_data["investments"].append(investment)
        save_user_data(current_user['id'], user_data)

        return redirect("/investments")

    except Exception as e:
        print(f"Ошибка при добавлении инвестиции: {e}")
        return redirect("/add-investment")


@app.route('/investment-reports')
def investment_reports_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    investments = user_data.get("investments", [])

    # Расчет расширенной статистики
    total_value = calculate_portfolio_value(investments)
    allocation = get_portfolio_allocation(investments)

    # Рассчитываем общую прибыль
    total_profit = 0
    total_invested = 0
    for inv in investments:
        if isinstance(inv, dict):
            current_value = inv.get("current_value", inv.get("amount", 0))
            purchase_value = inv.get("amount", 0)
            total_profit += current_value - purchase_value
            total_invested += purchase_value

    total_profit_percent = (total_profit / total_invested * 100) if total_invested > 0 else 0

    # Генерируем примеры диверсификации для разных профилей риска
    diversification_examples = [
        {
            "name": "Консервативный",
            "description": "Минимальный риск",
            "allocation": "20% акции, 60% облигации, 20% депозиты",
            "color": "#4CAF50"
        },
        {
            "name": "Умеренный",
            "description": "Баланс риска и доходности",
            "allocation": "50% акции, 40% облигации, 10% депозиты",
            "color": "#2196F3"
        },
        {
            "name": "Агрессивный",
            "description": "Максимальная доходность",
            "allocation": "80% акции, 15% облигации, 5% депозиты",
            "color": "#FF9800"
        }
    ]

    diversification_html = ""
    for example in diversification_examples:
        diversification_html += f'''
        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {example['color']};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: {example['color']};">{example['name']}</strong>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">{example['description']}</p>
                </div>
                <span style="font-weight: bold;">{example['allocation']}</span>
            </div>
        </div>
        '''

    content = f'''
    <div class="card-header">
        <h1 class="card-title" style="font-size: 28px;">Аналитика инвестиций</h1>
        <div>
            <a href="/investments" class="btn btn-secondary" style="padding: 10px 20px;">
                <i class="fas fa-arrow-left"></i> Назад к портфелю
            </a>
        </div>
    </div>

    <!-- Общая статистика -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #2196F3;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Общая прибыль</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: {'#4CAF50' if total_profit >= 0 else '#f44336'}">
                {'+' if total_profit >= 0 else ''}{total_profit:,.0f} ₽
            </div>
            <p style="color: {'#4CAF50' if total_profit_percent >= 0 else '#f44336'}; font-weight: bold;">
                ({total_profit_percent:+.1f}%)
            </p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #4CAF50;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Инвестировано</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #4CAF50;">{total_invested:,.0f} ₽</div>
            <p>Общая сумма вложений</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #FF9800;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Рентабельность</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #FF9800;">
    {((total_value / total_invested * 100) - 100) if total_invested > 0 else 0.0:+.1f}%
</div>
            <p>Доходность портфеля</p>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin: 30px 0;">
        <!-- Левая колонка: Примеры диверсификации -->
        <div class="card">
            <h3 style="margin-bottom: 20px; color: #333;">
                <i class="fas fa-balance-scale"></i> Примеры диверсификации
            </h3>
            <p style="color: #666; margin-bottom: 20px;">
                Выберите стратегию в зависимости от вашей готовности к риску:
            </p>
            {diversification_html}

            <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #eee;">
                <h4 style="color: #666; margin-bottom: 10px;">Советы:</h4>
                <ul style="padding-left: 20px; color: #555;">
                    <li style="margin-bottom: 8px;">Определите свой профиль риска</li>
                    <li style="margin-bottom: 8px;"> Следуйте выбранной стратегии распределения</li>
                    <li style="margin-bottom: 8px;"> Регулярно проводите ребалансировку</li>
                    <li>Инвестируйте на долгий срок для снижения рисков</li>
                </ul>
            </div>
        </div>

        <!-- Правая колонка: Подробное распределение -->
        <div class="card">
            <h3 style="margin-bottom: 20px; color: #333;">
                <i class="fas fa-chart-bar"></i> Детальное распределение
            </h3>

            {generate_detailed_allocation_html(allocation, total_value)}

            <div style="margin-top: 25px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h4 style="color: #666; margin-bottom: 10px;">Анализ диверсификации:</h4>
                <p style="color: #555; margin: 0;">
                    {get_diversification_analysis(len(allocation), total_value)}
                </p>
            </div>
        </div>
    </div>
    '''

    return get_base_html("Аналитика инвестиций", content)


def generate_detailed_allocation_html(allocation, total_value):
    """Генерация HTML для детального отображения распределения"""
    if not allocation:
        return '<p style="text-align: center; color: #666;">Нет данных для отображения</p>'

    html = '<div style="max-height: 300px; overflow-y: auto; padding-right: 10px;">'

    # Сортируем по убыванию доли
    sorted_allocation = sorted(allocation.items(), key=lambda x: x[1]["percentage"], reverse=True)

    for inv_type, stats in sorted_allocation:
        percentage = stats["percentage"]
        value = stats["value"]

        # Определяем цвет в зависимости от типа
        colors = {
            "Акции": "#4CAF50",
            "Облигации": "#2196F3",
            "Депозиты": "#FF9800",
            "Недвижимость": "#9C27B0",
            "ETF": "#00BCD4",
            "Криптовалюта": "#FF5722"
        }
        color = colors.get(inv_type, "#795548")

        html += f'''
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: {color};"></div>
                    <span style="font-weight: 500;">{inv_type}</span>
                </div>
                <span><strong>{percentage:.1f}%</strong></span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 12px; color: #666;">{value:,.0f} ₽</span>
                <span style="font-size: 12px; color: #666;">{(value / total_value * 100):.1f}% от портфеля</span>
            </div>
            <div style="height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                <div style="width: {percentage}%; height: 100%; background: {color}; border-radius: 4px;"></div>
            </div>
        </div>
        '''

    html += '</div>'
    return html


def get_diversification_analysis(num_types, total_value):
    """Анализ уровня диверсификации"""
    if total_value == 0:
        return "Начните инвестировать, чтобы получить анализ диверсификации."

    if num_types == 0:
        return "Портфель пуст. Добавьте активы для создания диверсифицированного портфеля."
    elif num_types == 1:
        return " Низкая диверсификация. Вы подвержены высокому риску. Добавьте активы других типов."
    elif num_types == 2:
        return " Средняя диверсификация. Хорошо, но можно лучше. Рассмотрите возможность добавления еще одного типа активов."
    elif num_types >= 3:
        return " Высокая диверсификация. Отличная работа! Ваш портфель хорошо защищен от рисков."
    else:
        return "Проведите анализ вашего портфеля для оптимизации распределения активов."

# Цели
@app.route('/goals')
def goals_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    goals = user_data.get("goals", [])

    # Сортируем цели: сначала просроченные, затем срочные, затем активные, затем завершенные
    def goal_sort_key(goal):
        if not isinstance(goal, dict):
            return (4, "")

        status = get_goal_status(goal)
        deadline = goal.get("deadline", "9999-12-31")

        status_order = {
            "overdue": 1,
            "urgent": 2,
            "active": 3,
            "good_progress": 3,
            "completed": 4,
            "unknown": 5
        }

        return (status_order.get(status, 5), deadline)

    goals_sorted = sorted(goals, key=goal_sort_key)

    # Генерация HTML для целей
    goals_html = ""
    for goal in goals_sorted:
        if not isinstance(goal, dict):
            continue

        progress = calculate_goal_progress(goal)
        status = get_goal_status(goal)
        saved = goal.get("saved", 0)
        target = goal.get("target", 1)

        # Определяем цвета и иконки по статусу
        status_colors = {
            "completed": {"color": "#4CAF50", "icon": "🏆", "text": "Достигнута"},
            "overdue": {"color": "#f44336", "icon": "⏰", "text": "Просрочена"},
            "urgent": {"color": "#FF9800", "icon": "🔥", "text": "Срочная"},
            "good_progress": {"color": "#2196F3", "icon": "📈", "text": "Хороший прогресс"},
            "active": {"color": "#2196F3", "icon": "🎯", "text": "Активная"},
            "unknown": {"color": "#9E9E9E", "icon": "❓", "text": "Неизвестно"}
        }

        status_info = status_colors.get(status, status_colors["unknown"])

        # Форматируем дату дедлайна
        deadline_str = goal.get("deadline", "")
        try:
            deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d')
            display_deadline = deadline_date.strftime('%d.%m.%Y')

            # Считаем дни до дедлайна
            today = datetime.now()
            days_left = (deadline_date - today).days
            days_text = f"Осталось {days_left} дней" if days_left >= 0 else f"Просрочено на {abs(days_left)} дней"
        except:
            display_deadline = deadline_str
            days_text = ""

        goals_html += f'''
        <div style="background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-left: 5px solid {status_info['color']};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                <div>
                    <h3 style="margin: 0 0 5px 0; color: #333; font-size: 18px;">
                        {status_info['icon']} {goal.get('name', 'Без названия')}
                    </h3>
                    <p style="margin: 0; color: #666; font-size: 14px;">
                        {goal.get('description', '')}
                    </p>
                </div>
                <span style="background: {status_info['color']}15; color: {status_info['color']}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">
                    {status_info['text']}
                </span>
            </div>

            <!-- Прогресс-бар -->
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="color: #666; font-size: 14px;">Прогресс: {progress:.1f}%</span>
                    <span style="color: #666; font-size: 14px;">{saved:,.0f} ₽ / {target:,.0f} ₽</span>
                </div>
                <div style="height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden;">
                    <div style="width: {progress}%; height: 100%; background: {status_info['color']}; border-radius: 5px;"></div>
                </div>
            </div>

            <!-- Детали цели -->
            <div style="display: flex; justify-content: space-between; font-size: 13px; color: #666;">
                <div>
                    <i class="fas fa-calendar-alt"></i> До {display_deadline}
                    {f'<br><span style="font-size: 11px; color: {status_info["color"]};">{days_text}</span>' if days_text else ''}
                </div>
                <div>
                    Осталось: <strong style="color: {status_info['color']};">{target - saved:,.0f} ₽</strong>
                </div>
            </div>

            <!-- Кнопки управления -->
            <div style="display: flex; gap: 10px; margin-top: 15px;">
                <button onclick="addToGoal({goal.get('id', 0)})" class="btn" style="background: #4CAF50; color: white; padding: 8px 16px; font-size: 12px;">
                    <i class="fas fa-plus"></i> Добавить средства
                </button>
                <button onclick="editGoal({goal.get('id', 0)})" class="btn" style="background: #2196F3; color: white; padding: 8px 16px; font-size: 12px;">
                    <i class="fas fa-edit"></i> Редактировать
                </button>
                <button onclick="deleteGoal({goal.get('id', 0)})" class="btn" style="background: #f0f0f0; color: #666; padding: 8px 16px; font-size: 12px;">
                    <i class="fas fa-trash"></i> Удалить
                </button>
            </div>
        </div>
        '''

    if not goals_html:
        goals_html = '''
        <div style="text-align: center; padding: 50px; color: #666;">
            <div style="font-size: 64px; margin-bottom: 20px;">🎯</div>
            <p style="font-size: 18px; margin-bottom: 10px;">У вас пока нет финансовых целей</p>
            <p style="margin-bottom: 20px;">Создайте свою первую цель, чтобы начать копить на мечту!</p>
            <a href="/add-goal" class="btn btn-primary" style="padding: 10px 20px;">
                <i class="fas fa-plus"></i> Создать первую цель
            </a>
        </div>
        '''

    content = f'''
    <div class="card-header">
        <h1 class="card-title" style="font-size: 28px;">Финансовые цели</h1>
        <div>
            <a href="/add-goal" class="btn btn-primary" style="padding: 10px 20px;">
                <i class="fas fa-plus"></i> Новая цель
            </a>
        </div>
    </div>

    <!-- Общая статистика целей -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #4CAF50;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Всего целей</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #4CAF50;">{len(goals)}</div>
            <p>Количество активных целей</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #2196F3;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Общая цель</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #2196F3;">
                {sum(g.get("target", 0) for g in goals if isinstance(g, dict)):,.0f} ₽
            </div>
            <p>Сумма всех целей</p>
        </div>

        <div style="background: white; border-radius: 10px; padding: 25px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-top: 5px solid #FF9800;">
            <div style="color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Уже накоплено</div>
            <div style="font-size: 36px; font-weight: bold; margin: 10px 0; color: #FF9800;">
                {sum(g.get("saved", 0) for g in goals if isinstance(g, dict)):,.0f} ₽
            </div>
            <p>Сумма всех накоплений</p>
        </div>
    </div>

    <!-- Список целей -->
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 style="color: #333;">
                <i class="fas fa-bullseye"></i> Мои цели
            </h3>
        </div>

        {goals_html}
    </div>

    <!-- JavaScript для управления целями -->
    <script>
    function addToGoal(goalId) {{
        const amount = prompt("Сколько средств добавить к цели? (₽)", "1000");
        if (amount && !isNaN(amount) && parseFloat(amount) > 0) {{
            fetch(`/api/goals/${{goalId}}/add`, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                }},
                body: `amount=${{amount}}`
            }}).then(response => {{
                if (response.ok) {{
                    window.location.reload();
                }} else {{
                    alert('Ошибка при добавлении средств');
                }}
            }});
        }}
    }}

    function editGoal(goalId) {{
        window.location.href = `/edit-goal?id=${{goalId}}`;
    }}

    function deleteGoal(goalId) {{
        if (confirm('Вы уверены, что хотите удалить эту цель?')) {{
            fetch(`/api/goals/${{goalId}}/delete`, {{
                method: 'DELETE'
            }}).then(response => {{
                if (response.ok) {{
                    window.location.reload();
                }} else {{
                    alert('Ошибка при удалении цели');
                }}
            }});
        }}
    }}

    function filterGoals(filter) {{
        // Простая фильтрация - можно переписать на более сложную
        alert('Фильтр "' + filter + '" - в простой версии показаны все цели');
    }}
    </script>
    '''

    return get_base_html("Цели", content)


@app.route('/add-goal')
def add_goal_page():
    content = '''
    <h1 style="color: #333; margin-bottom: 20px;">Создать финансовую цель</h1>

    <div class="card">
        <form action="/api/add-goal" method="POST">
            <div class="form-group">
                <label for="name">Название цели</label>
                <input type="text" id="name" name="name" required 
                       placeholder="Например: Новый автомобиль, Покупка квартиры, Отпуск мечты" 
                       style="width: 100%; padding: 12px;">
            </div>

            <div class="form-group">
                <label for="description">Описание цели (необязательно)</label>
                <textarea id="description" name="description" rows="2" 
                          placeholder="Дополнительные детали, мотивация или план достижения цели" 
                          style="width: 100%; padding: 12px; resize: vertical;"></textarea>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="form-group">
                    <label for="target">Целевая сумма (₽)</label>
                    <input type="number" id="target" name="target" step="0.01" min="1" required 
                           placeholder="1000000" style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="saved">Уже накоплено (₽)</label>
                    <input type="number" id="saved" name="saved" step="0.01" min="0" 
                           placeholder="0" style="width: 100%; padding: 12px;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="form-group">
                    <label for="deadline">Дата достижения цели</label>
                    <input type="date" id="deadline" name="deadline" 
                           value="''' + (datetime.now().replace(year=datetime.now().year + 1)).strftime('%Y-%m-%d') + '''" 
                           required style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="priority">Приоритет (от 1 до 10)</label>
                    <select id="priority" name="priority" style="width: 100%; padding: 12px;">
                        <option value="1">1 - Самый низкий</option>
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="5" selected>5 - Средний</option>
                        <option value="6">6</option>
                        <option value="7">7</option>
                        <option value="8">8</option>
                        <option value="9">9</option>
                        <option value="10">10 - Самый высокий</option>
                    </select>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 30px;">
                <button type="submit" class="btn btn-primary" style="padding: 12px 24px;">
                    <i class="fas fa-save"></i> Создать цель
                </button>
                <a href="/goals" class="btn" style="background: #f0f0f0; padding: 12px 24px;">Отмена</a>
            </div>
        </form>
    </div>

    '''

    return get_base_html("Создать цель", content)


@app.route('/api/add-goal', methods=['POST'])
def api_add_goal():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        target = float(request.form.get("target", 0))
        saved = float(request.form.get("saved", 0))

        goal = {
            "id": len(user_data.get("goals", [])) + 1,
            "name": request.form.get("name", ""),
            "description": request.form.get("description", ""),
            "target": target,
            "saved": saved,
            "deadline": request.form.get("deadline", datetime.now().strftime("%Y-%m-%d")),
            "priority": int(request.form.get("priority", 5)),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "progress": (saved / target * 100) if target > 0 else 0
        }

        # Инициализируем список целей, если его нет
        if "goals" not in user_data:
            user_data["goals"] = []

        user_data["goals"].append(goal)
        save_user_data(current_user['id'], user_data)

        return redirect("/goals")

    except Exception as e:
        print(f"Ошибка при создании цели: {e}")
        return redirect("/add-goal")


@app.route('/api/goals/<int:goal_id>/add', methods=['POST'])
def api_add_to_goal(goal_id):
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        amount = float(request.form.get("amount", 0))

        goals = user_data.get("goals", [])
        for goal in goals:
            if isinstance(goal, dict) and goal.get("id") == goal_id:
                current_saved = goal.get("saved", 0)
                goal["saved"] = current_saved + amount

                # Пересчитываем прогресс
                target = goal.get("target", 1)
                goal["progress"] = (goal["saved"] / target * 100) if target > 0 else 0

                save_user_data(current_user['id'], user_data)
                return jsonify({"success": True, "new_amount": goal["saved"]})

        return jsonify({"success": False, "error": "Цель не найдена"}), 404

    except Exception as e:
        print(f"Ошибка при добавлении средств к цели: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/goals/<int:goal_id>/delete', methods=['DELETE'])
def api_delete_goal(goal_id):
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        goals = user_data.get("goals", [])
        new_goals = []
        deleted = False

        for goal in goals:
            if isinstance(goal, dict) and goal.get("id") == goal_id:
                deleted = True
                continue
            new_goals.append(goal)

        if deleted:
            user_data["goals"] = new_goals
            save_user_data(current_user['id'], user_data)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Цель не найдена"}), 404

    except Exception as e:
        print(f"Ошибка при удалении цели: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/edit-goal')
def edit_goal_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    goal_id = int(request.args.get('id', 0))

    goal = None
    for g in user_data.get("goals", []):
        if isinstance(g, dict) and g.get("id") == goal_id:
            goal = g
            break

    if not goal:
        return redirect("/goals")

    content = f'''
    <h1 style="color: #333; margin-bottom: 20px;">Редактировать цель</h1>

    <div class="card">
        <form action="/api/edit-goal" method="POST">
            <input type="hidden" name="id" value="{goal_id}">

            <div class="form-group">
                <label for="name">Название цели</label>
                <input type="text" id="name" name="name" required 
                       value="{goal.get('name', '')}"
                       style="width: 100%; padding: 12px;">
            </div>

            <div class="form-group">
                <label for="description">Описание цели</label>
                <textarea id="description" name="description" rows="2" 
                          style="width: 100%; padding: 12px; resize: vertical;">{goal.get('description', '')}</textarea>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="form-group">
                    <label for="target">Целевая сумма (₽)</label>
                    <input type="number" id="target" name="target" step="0.01" min="1" required 
                           value="{goal.get('target', 0)}"
                           style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="saved">Уже накоплено (₽)</label>
                    <input type="number" id="saved" name="saved" step="0.01" min="0" 
                           value="{goal.get('saved', 0)}"
                           style="width: 100%; padding: 12px;">
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="form-group">
                    <label for="deadline">Дата достижения цели</label>
                    <input type="date" id="deadline" name="deadline" 
                           value="{goal.get('deadline', '')}"
                           required style="width: 100%; padding: 12px;">
                </div>

                <div class="form-group">
                    <label for="priority">Приоритет (от 1 до 10)</label>
                    <select id="priority" name="priority" style="width: 100%; padding: 12px;">
                        {''.join([f'<option value="{i}" {"selected" if goal.get("priority", 5) == i else ""}>{i} - {"Самый низкий" if i == 1 else "Самый высокий" if i == 10 else ""}</option>' for i in range(1, 11)])}
                    </select>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 30px;">
                <button type="submit" class="btn btn-primary" style="padding: 12px 24px;">
                    <i class="fas fa-save"></i> Сохранить изменения
                </button>
                <a href="/goals" class="btn" style="background: #f0f0f0; padding: 12px 24px;">Отмена</a>
            </div>
        </form>
    </div>
    '''

    return get_base_html("Редактировать цель", content)


@app.route('/api/edit-goal', methods=['POST'])
def api_edit_goal():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    try:
        goal_id = int(request.form.get("id", 0))
        target = float(request.form.get("target", 0))
        saved = float(request.form.get("saved", 0))

        goals = user_data.get("goals", [])
        for goal in goals:
            if isinstance(goal, dict) and goal.get("id") == goal_id:
                goal["name"] = request.form.get("name", "")
                goal["description"] = request.form.get("description", "")
                goal["target"] = target
                goal["saved"] = saved
                goal["deadline"] = request.form.get("deadline", "")
                goal["priority"] = int(request.form.get("priority", 5))
                goal["progress"] = (saved / target * 100) if target > 0 else 0

                save_user_data(current_user['id'], user_data)
                return redirect("/goals")

        return redirect("/goals")

    except Exception as e:
        print(f"Ошибка при редактировании цели: {e}")
        return redirect("/edit-goal?id=" + request.form.get("id", ""))


@app.route('/reports')
def reports_page():
    current_user = get_current_user()
    if not current_user:
        return redirect('/login')

    user_data = load_user_data(current_user['id'])
    if not user_data:
        return redirect('/login')

    transactions = user_data.get("transactions", [])
    investments = user_data.get("investments", [])
    goals = user_data.get("goals", [])

    # Получаем данные для отчетов
    monthly_data = get_monthly_summary(transactions)
    expense_categories = get_category_summary(transactions, "expense")
    income_categories = get_category_summary(transactions, "income")
    investment_summary = get_investment_summary(investments)

    # Генерация HTML для месячной сводки
    monthly_html = ""
    for month_key, month_data in monthly_data.items():
        monthly_html += f'''
        <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <strong style="color: #333;">{month_data['name']}</strong>
                <span style="font-weight: bold; color: {'#4CAF50' if month_data['balance'] >= 0 else '#f44336'}">
                    {month_data['balance']:+,.0f} ₽
                </span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 13px;">
                <div style="text-align: center;">
                    <div style="color: #4CAF50; font-weight: 500;">+{month_data['income']:,.0f} ₽</div>
                    <div style="color: #666; font-size: 11px;">Доходы</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #f44336; font-weight: 500;">-{month_data['expense']:,.0f} ₽</div>
                    <div style="color: #666; font-size: 11px;">Расходы</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #666; font-weight: 500;">{month_data['transactions']}</div>
                    <div style="color: #666; font-size: 11px;">Операций</div>
                </div>
            </div>
        </div>
        '''

    if not monthly_html:
        monthly_html = '<p style="text-align: center; color: #666; padding: 20px;">Нет данных за последние месяцы</p>'

    # Генерация HTML для категорий расходов
    expenses_html = ""
    for category, cat_data in expense_categories.items():
        expenses_html += f'''
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 14px;">{category}</span>
                <span style="font-weight: 500;">{cat_data['amount']:,.0f} ₽</span>
            </div>
            <div style="height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                <div style="width: {cat_data['percentage']}%; height: 100%; background: #f44336; border-radius: 4px;"></div>
            </div>
            <div style="font-size: 11px; color: #666; text-align: right; margin-top: 3px;">
                {cat_data['percentage']:.1f}% • {cat_data['count']} операций
            </div>
        </div>
        '''

    if not expenses_html:
        expenses_html = '<p style="text-align: center; color: #666; padding: 20px;">Нет данных по расходам</p>'

    # Генерация HTML для категорий доходов
    incomes_html = ""
    for category, cat_data in income_categories.items():
        incomes_html += f'''
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 14px;">{category}</span>
                <span style="font-weight: 500;">{cat_data['amount']:,.0f} ₽</span>
            </div>
            <div style="height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                <div style="width: {cat_data['percentage']}%; height: 100%; background: #4CAF50; border-radius: 4px;"></div>
            </div>
            <div style="font-size: 11px; color: #666; text-align: right; margin-top: 3px;">
                {cat_data['percentage']:.1f}% • {cat_data['count']} операций
            </div>
        </div>
        '''

    if not incomes_html:
        incomes_html = '<p style="text-align: center; color: #666; padding: 20px;">Нет данных по доходам</p>'

    # Генерация HTML для инвестиций
    investments_html = ""
    if investment_summary["by_type"]:
        for inv_type, type_data in investment_summary["by_type"].items():
            profit_color = "#4CAF50" if type_data["profit"] >= 0 else "#f44336"
            profit_sign = "+" if type_data["profit"] >= 0 else ""

            investments_html += f'''
            <div style="background: white; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 500;">{inv_type}</div>
                        <div style="font-size: 11px; color: #666;">{type_data['count']} активов</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-weight: bold;">{type_data['value']:,.0f} ₽</div>
                        <div style="font-size: 11px; color: {profit_color};">
                            {profit_sign}{type_data['profit']:,.0f} ₽
                        </div>
                    </div>
                </div>
            </div>
            '''
    else:
        investments_html = '<p style="text-align: center; color: #666; padding: 20px;">Нет инвестиционных активов</p>'

    # Общая статистика
    total_income = sum(t.get("amount", 0) for t in transactions if isinstance(t, dict) and t.get("amount", 0) > 0)
    total_expense = sum(abs(t.get("amount", 0)) for t in transactions if isinstance(t, dict) and t.get("amount", 0) < 0)
    total_balance = total_income - total_expense

    total_goals_target = sum(g.get("target", 0) for g in goals if isinstance(g, dict))
    total_goals_saved = sum(g.get("saved", 0) for g in goals if isinstance(g, dict))
    goals_progress = (total_goals_saved / total_goals_target * 100) if total_goals_target > 0 else 0

    content = f'''
    <div class="card-header">
        <h1 class="card-title" style="font-size: 28px;">Финансовые отчеты</h1>
        <div>
            <button onclick="window.print()" class="btn btn-secondary" style="padding: 10px 20px;">
                <i class="fas fa-print"></i> Печать
            </button>
        </div>
    </div>

    <!-- Общая статистика -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 25px 0;">
        <div style="background: white; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Общий баланс</div>
            <div style="font-size: 28px; font-weight: bold; margin: 8px 0; color: {'#4CAF50' if total_balance >= 0 else '#f44336'}">
                {total_balance:+,.0f} ₽
            </div>
            <div style="font-size: 11px; color: #666;">Доходы: {total_income:,.0f} ₽</div>
            <div style="font-size: 11px; color: #666;">Расходы: {total_expense:,.0f} ₽</div>
        </div>

        <div style="background: white; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Инвестиции</div>
            <div style="font-size: 28px; font-weight: bold; margin: 8px 0; color: #2196F3;">
                {investment_summary['total_value']:,.0f} ₽
            </div>
            <div style="font-size: 11px; color: {'#4CAF50' if investment_summary['total_profit'] >= 0 else '#f44336'}">
                {investment_summary['total_profit']:+,.0f} ₽ ({investment_summary['profit_percentage']:+.1f}%)
            </div>
            <div style="font-size: 11px; color: #666;">{len(investments)} активов</div>
        </div>

        <div style="background: white; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Цели</div>
            <div style="font-size: 28px; font-weight: bold; margin: 8px 0; color: #FF9800;">
                {total_goals_saved:,.0f} ₽
            </div>
            <div style="font-size: 11px; color: #666;">из {total_goals_target:,.0f} ₽</div>
            <div style="font-size: 11px; color: #4CAF50; font-weight: 500;">
                {goals_progress:.1f}% выполнено
            </div>
        </div>

        <div style="background: white; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.05);">
            <div style="color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Всего операций</div>
            <div style="font-size: 28px; font-weight: bold; margin: 8px 0; color: #9C27B0;">
                {len(transactions)}
            </div>
            <div style="font-size: 11px; color: #666;">транзакций</div>
            <div style="font-size: 11px; color: #666;">в системе</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin: 25px 0;">
        <!-- Левая колонка: Месячная статистика -->
        <div class="card">
            <h3 style="margin-bottom: 15px; color: #333; font-size: 18px;">
                <i class="fas fa-calendar-alt"></i> Помесячная сводка
            </h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                Динамика доходов и расходов за последние 6 месяцев
            </p>
            {monthly_html}
        </div>

        <!-- Правая колонка: Категории расходов -->
        <div class="card">
            <h3 style="margin-bottom: 15px; color: #333; font-size: 18px;">
                <i class="fas fa-chart-pie"></i> Расходы по категориям
            </h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                На что больше всего тратите
            </p>
            {expenses_html}
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin: 25px 0;">
        <!-- Левая колонка: Доходы по категориям -->
        <div class="card">
            <h3 style="margin-bottom: 15px; color: #333; font-size: 18px;">
                <i class="fas fa-money-bill-wave"></i> Доходы по категориям
            </h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                Источники поступлений
            </p>
            {incomes_html}
        </div>

        <!-- Правая колонка: Инвестиционный портфель -->
        <div class="card">
            <h3 style="margin-bottom: 15px; color: #333; font-size: 18px;">
                <i class="fas fa-chart-line"></i> Инвестиции по типам
            </h3>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                Распределение инвестиционного портфеля
            </p>
            {investments_html}

            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
                <div style="display: flex; justify-content: space-between; font-size: 14px;">
                    <span>Общая стоимость:</span>
                    <span style="font-weight: bold;">{investment_summary['total_value']:,.0f} ₽</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 14px; margin-top: 5px;">
                    <span>Общая прибыль:</span>
                    <span style="font-weight: bold; color: {'#4CAF50' if investment_summary['total_profit'] >= 0 else '#f44336'}">
                        {investment_summary['total_profit']:+,.0f} ₽
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Экспорт данных -->
    <div class="card" style="margin-top: 20px; background: #f8f9fa;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin-bottom: 5px; color: #333; font-size: 18px;">
                    <i class="fas fa-download"></i> Экспорт данных
                </h3>
                <p style="color: #666; font-size: 14px; margin: 0;">
                    Скачайте полные отчеты для детального анализа
                </p>
            </div>
            <div>
                <a href="/api/export/csv" class="btn btn-primary" style="padding: 8px 16px; margin-right: 10px;">
                    <i class="fas fa-file-csv"></i> CSV
                </a>
                <a href="/api/export/json" class="btn btn-secondary" style="padding: 8px 16px;">
                    <i class="fas fa-file-code"></i> JSON
                </a>
            </div>
        </div>
    </div>
    '''

    return get_base_html("Отчеты", content)


# СБРОС ДАННЫХ
@app.route('/reset-data')
def reset_data_page():
    """Страница подтверждения сброса данных"""
    content = '''
    <h1 style="color: #333; margin-bottom: 30px;">Сброс данных</h1>

    <div class="card" style="background: #fff3e0; border-left: 5px solid #FF9800;">
        <div style="text-align: center; padding: 20px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 64px; color: #FF9800; margin-bottom: 20px;"></i>
            <h3 style="color: #FF9800; margin-bottom: 15px;">Внимание! Это необратимое действие</h3>
            <p style="color: #666; margin-bottom: 20px;">
                Вы собираетесь удалить ВСЕ данные приложения. Это действие нельзя отменить.
                Все транзакции, инвестиции и цели будут безвозвратно удалены.
            </p>
        </div>
    </div>

    <div class="card">
        <h3 style="margin-bottom: 20px; color: #333;">
            <i class="fas fa-trash-alt"></i> Что будет удалено:
        </h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div style="background: #ffebee; padding: 15px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <i class="fas fa-exchange-alt" style="color: #f44336;"></i>
                    <strong>Все транзакции</strong>
                </div>
                <p style="color: #666; margin: 0; font-size: 14px;">Доходы, расходы, история операций</p>
            </div>

            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <i class="fas fa-chart-line" style="color: #2196F3;"></i>
                    <strong>Инвестиции</strong>
                </div>
                <p style="color: #666; margin: 0; font-size: 14px;">Весь портфель, акции, облигации</p>
            </div>

            <div style="background: #fff8e1; padding: 15px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <i class="fas fa-bullseye" style="color: #FF9800;"></i>
                    <strong>Финансовые цели</strong>
                </div>
                <p style="color: #666; margin: 0; font-size: 14px;">Все цели и накопления</p>
            </div>

            <div style="background: #f3e5f5; padding: 15px; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <i class="fas fa-chart-bar" style="color: #9C27B0;"></i>
                    <strong>Статистика</strong>
                </div>
                <p style="color: #666; margin: 0; font-size: 14px;">Вся история и отчеты</p>
            </div>
        </div>

        <div style="display: flex; gap: 15px; margin-top: 30px; justify-content: center;">
            <button onclick="confirmReset()" class="btn btn-danger" style="padding: 12px 24px;">
                <i class="fas fa-trash"></i> Да, удалить все данные
            </button>
            <a href="/" class="btn" style="background: #f0f0f0; padding: 12px 24px;">
                <i class="fas fa-times"></i> Отмена
            </a>
        </div>
    </div>

    <div class="card" style="background: #f8f9fa; margin-top: 20px;">
        <div style="display: flex; gap: 15px; align-items: flex-start;">
            <i class="fas fa-lightbulb" style="color: #FF9800; font-size: 24px; margin-top: 5px;"></i>
            <div>
                <h4 style="color: #666; margin-bottom: 10px;">Рекомендация</h4>
                <p style="color: #666; margin: 0;">
                    Перед сбросом данных рекомендуется экспортировать их через раздел 
                    <a href="/export" style="color: #2196F3; font-weight: 500;">Экспорт</a> 
                    для сохранения резервной копии.
                </p>
            </div>
        </div>
    </div>

    <script>
    function confirmReset() {
        if (confirm('ВНИМАНИЕ!\\n\\nВы уверены, что хотите удалить ВСЕ данные?\\nЭто действие НЕЛЬЗЯ отменить!\\n\\n Сначала сделайте резервную копию через Экспорт\\n Все данные будут удалены безвозвратно')) {
            // Показываем индикатор загрузки
            const buttons = document.querySelectorAll('button, .btn');
            buttons.forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Удаление...';
            });

            // Выполняем сброс
            fetch('/api/reset-data', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Данные успешно сброшены!');
                    window.location.href = '/';
                } else {
                    alert('Ошибка: ' + data.error);
                    window.location.reload();
                }
            })
            .catch(error => {
                alert('Ошибка при сбросе данных');
                window.location.reload();
            });
        }
    }
    </script>
    '''

    return get_base_html("Сброс данных", content)


@app.route('/api/reset-data', methods=['POST'])
def api_reset_data():
    """API для сброса всех данных"""
    try:
        # Создаем новую структуру данных
        new_data = create_default_data()

        # Сохраняем в файл
        save_data(new_data)

        return jsonify({
            "success": True,
            "message": "Данные успешно сброшены",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        print(f"Ошибка при сбросе данных: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
if __name__ == '__main__':
    print("=" * 70)
    print(" ФИНАНСОВЫЙ МЕНЕДЖЕР ЗАПУЩЕН!")
    print("=" * 70)
    print(" Главная страница:      http://localhost:5000")
    print(" Транзакции:            http://localhost:5000/transactions")
    print(" Инвестиции:            http://localhost:5000/investments")
    print(" Цели:                  http://localhost:5000/goals")
    print(" Отчеты:                http://localhost:5000/reports")
    print(" Экспорт данных:        http://localhost:5000/export")
    print("=" * 70)
    print(" Быстрое добавление:")
    print("   Доход:                 http://localhost:5000/add-transaction?type=income")
    print("   Расход:                http://localhost:5000/add-transaction?type=expense")
    print("   Сброс данных:          http://localhost:5000/reset-data")
    print("=" * 70)
    print(" Для остановки нажмите Ctrl+C")
    print("=" * 70)

    # Проверяем и создаем файл данных
    if not os.path.exists(DATA_FILE):
        print(" Создаем файл данных...")
        save_data(create_default_data())

    app.run(debug=True, port=5000)