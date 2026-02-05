from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
import json
from datetime import datetime
import csv
import io
import hashlib
import os
from modules.decorators import *
from modules.utils import *


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DATA_FILE = "finance_data.json"


@app.template_filter('filesizeformat')
def filesizeformat_filter(value):
    """Форматирование размера файла (как в Django)"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0 bytes"

    # КБ в байты
    value = value * 1024

    if value < 1024:
        return f"{value:.0f} bytes"
    elif value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    elif value < 1024 * 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    else:
        return f"{value / (1024 * 1024 * 1024):.1f} GB"

@app.context_processor
def inject_utils():
    """Добавляет функции из utils во все шаблоны"""
    from modules.utils import (
        format_currency,
        format_date,
        get_transactions_table,
        get_recent_transactions_table,
        calculate_portfolio_value,
        get_portfolio_allocation,
        generate_recommendations,
        get_investment_summary,
        # ДОБАВЛЯЕМ ФУНКЦИИ ДЛЯ ОТЧЕТОВ:
        get_monthly_summary,
        get_category_summary,
        calculate_goal_progress,
        get_goal_status
    )
    return {
        'format_currency': format_currency,
        'format_date': format_date,
        'get_transactions_table': get_transactions_table,
        'get_recent_transactions_table': get_recent_transactions_table,
        'calculate_portfolio_value': calculate_portfolio_value,
        'get_portfolio_allocation': get_portfolio_allocation,
        'generate_recommendations': generate_recommendations,
        'get_investment_summary': get_investment_summary,
        # ДОБАВЛЯЕМ:
        'get_monthly_summary': get_monthly_summary,
        'get_category_summary': get_category_summary,
        'calculate_goal_progress': calculate_goal_progress,
        'get_goal_status': get_goal_status,
        'datetime': datetime,
        'now': datetime.now()
    }
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
        # ОБЩИЕ ДАННЫЕ:
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


def generate_menu_components(current_user, current_title):
    """Генерация компонентов меню"""
    if not current_user:
        # Если пользователь не авторизован
        menu_links = '''
        <div class="nav-links-mobile">
            <a href="/login" class="nav-link">
                <i class="fas fa-sign-in-alt"></i> Войти
            </a>
            <a href="/register" class="nav-link">
                <i class="fas fa-user-plus"></i> Регистрация
            </a>
        </div>
        '''
        user_info = ''
        mobile_menu = ''
    else:
        # Для авторизованных пользователей
        active_routes = {
            'Главная': '/',
            'Транзакции': '/transactions',
            'Инвестиции': '/investments',
            'Цели': '/goals',
            'Отчеты': '/reports',
            'Экспорт': '/export',
            'Сброс': '/reset-data'
        }

        icons = {
            'Главная': 'home',
            'Транзакции': 'exchange-alt',
            'Инвестиции': 'chart-line',
            'Цели': 'bullseye',
            'Отчеты': 'chart-pie',
            'Экспорт': 'download',
            'Сброс': 'trash-alt'
        }

        menu_links = ''
        for route_name, route_url in active_routes.items():
            is_active = "active" if current_title == route_name else ""
            icon = icons.get(route_name, 'circle')
            menu_links += f'''
            <a href="{route_url}" class="nav-link {is_active}">
                <i class="fas fa-{icon}"></i> <span class="nav-text">{route_name}</span>
            </a>
            '''

        menu_links += f'''
        <a href="/logout" class="nav-link logout-link">
            <i class="fas fa-sign-out-alt"></i> <span class="nav-text">Выйти</span>
        </a>
        '''

        user_info = f'''
        <div class="user-info">
            <i class="fas fa-user-circle"></i>
            <div class="user-details">
                <div class="username">{current_user['username']}</div>
                <div class="user-role">Пользователь</div>
            </div>
        </div>
        '''

        mobile_menu = '''
        <div class="mobile-menu-toggle" onclick="toggleMobileMenu()">
            <i class="fas fa-bars"></i>
        </div>
        '''

    return menu_links, user_info, mobile_menu
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

    all_data = load_data()
    # Находим нужного пользователя
    for i, user in enumerate(all_data.get("users", [])):
        if user.get("id") == user_id:

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

# АВТОРИЗАЦИЯ
@app.route('/login', methods=['GET', 'POST'])
def login():
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

    return render_template(
        'login.html',
        current_user=None,
        current_title="Вход",
        current_year=datetime.now().year
    )
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

    return render_template(
        'register.html',
        current_user=None,
        current_title="Регистрация")

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()  # Очищаем все данные сессии
    return redirect('/login')
#  ГЛАВНАЯ СТРАНИЦА
@app.route('/')
@login_required
@load_user_data_decorator
def index(user_data, current_user):
    # Получаем данные
    transactions = user_data.get("transactions", [])
    incomes = [t for t in transactions if isinstance(t, dict) and t.get("type") == "income"]
    expenses = [t for t in transactions if isinstance(t, dict) and t.get("type") == "expense"]

    total_income = sum(t.get("amount", 0) for t in incomes if isinstance(t.get("amount"), (int, float)))
    total_expense = sum(abs(t.get("amount", 0)) for t in expenses if isinstance(t.get("amount"), (int, float)))
    balance = total_income - total_expense

    # Последние транзакции
    recent_transactions = transactions[-5:] if len(transactions) > 5 else transactions

    # Секция инвестиций
    investments = user_data.get("investments", [])
    recent_investments = investments[-3:] if len(investments) > 3 else investments

    return render_template(
        'index.html',
        current_user=current_user,
        current_title="Главная",
        current_year=datetime.now().year,
        balance=balance,
        total_income=total_income,
        total_expense=total_expense,
        recent_transactions=recent_transactions,
        investments=investments,
        recent_investments=recent_investments,
        format_currency=format_currency,  # передаем функцию в шаблон
        format_investment_html=format_investment_html,
        get_recent_transactions_table=get_recent_transactions_table
    )

# ДОБАВЛЕНИЕ ТРАНЗАКЦИИ
@app.route('/add-transaction')
@login_required
@load_user_data_decorator
def add_transaction_page(user_data, current_user):
    trans_type = request.args.get('type', 'income')

    # Безопасно получаем категории
    categories_data = user_data.get("categories", {})
    if isinstance(categories_data, dict):
        categories = categories_data.get(trans_type, [])
    else:
        categories = ["Зарплата", "Еда", "Транспорт", "Другое"]

    # Определяем переменные для шаблона
    if trans_type == 'income':
        page_title = "Добавить доход"
        button_text = "Сохранить доход"
        button_class = "btn-primary"
    else:
        page_title = "Добавить расход"
        button_text = "Сохранить расход"
        button_class = "btn-danger"

    return render_template(
        'add_transaction.html',
        current_user=current_user,
        current_title=page_title,
        trans_type=trans_type,
        categories=categories,
        page_title=page_title,
        button_text=button_text,
        button_class=button_class,
        today=datetime.now().strftime('%Y-%m-%d'))
# API для добавления транзакции
@app.route('/api/add-transaction', methods=['POST'])
@login_required
@load_user_data_decorator
def api_add_transaction(user_data, current_user):
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
@login_required
@load_user_data_decorator
def transactions_page(user_data, current_user):
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

    return render_template(
        'transactions.html',
        current_user=current_user,
        current_title="Транзакции",
        transactions=transactions,
        transactions_sorted=transactions_sorted,
        get_transactions_table = get_transactions_table,
        format_currency=format_currency,
        format_date=format_date
    )
#ЭКСПОРТ
@app.route('/export')
@login_required
@load_user_data_decorator
def export_page(user_data, current_user):
    """Страница экспорта данных"""
    transactions = user_data.get("transactions", [])
    investments = user_data.get("investments", [])
    goals = user_data.get("goals", [])

    # Подсчитываем статистику
    transactions_count = len(transactions)
    investments_count = len(investments)
    goals_count = len(goals)

    # Примерный размер данных (очень грубая оценка)
    total_size = (
                         len(json.dumps(transactions)) +
                         len(json.dumps(investments)) +
                         len(json.dumps(goals))
                 ) / 1024  # в КБ

    return render_template(
        'export.html',
        current_title="Экспорт",
        current_user=current_user,
        current_year=datetime.now().year,
        transactions_count=transactions_count,
        investments_count=investments_count,
        goals_count=goals_count,
        total_size=total_size
    )

# API для экспорта CSV
@app.route('/api/export/csv')
@login_required
@load_user_data_decorator
def export_csv(user_data, current_user):
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
@login_required
@load_user_data_decorator
def export_json(user_data, current_user):
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
@login_required
@load_user_data_decorator
def investments_page(user_data, current_user):
    investments = user_data.get("investments", [])

    # Добавьте эти данные (если они есть в user_data):
    risk_profiles = user_data.get("risk_profiles", [])
    risk_profile_current = current_user.get("risk_profile", 2)

    # Расчет статистики
    total_value = calculate_portfolio_value(investments)
    allocation = get_portfolio_allocation(investments)

    # Исправленный вызов с тремя аргументами:
    recommendations = generate_recommendations(
        investments,
        risk_profiles,
        risk_profile_current
    )

    return render_template(
        'investments.html',
        current_title="Инвестиции",
        current_user=current_user,
        current_year=datetime.now().year,
        investments=investments,
        total_value=total_value,
        allocation=allocation,
        recommendations=recommendations
    )


@app.route('/add-investment')
@login_required
@load_user_data_decorator
def add_investment_page(user_data, current_user):
    investment_types = user_data.get("investment_types", ["Акции", "Облигации", "Депозиты", "Недвижимость"])

    return render_template(
        'add_investment.html',
        current_title="Добавить инвестицию",
        current_user=get_current_user,
        current_year=datetime.now().year,
        investment_types=investment_types,
        today=datetime.now().strftime('%Y-%m-%d'))
# добавление инвестиций
@app.route('/api/add-investment', methods=['POST'])
@login_required
@load_user_data_decorator
def api_add_investment(user_data, current_user):
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
@login_required
@load_user_data_decorator
def investment_reports_page(user_data, current_user):
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

    investment_summary = get_investment_summary(investments)

    return render_template(
        'investment_reports.html',
        current_title="Аналитика инвестиций",
        current_user=current_user,
        current_year=datetime.now().year,
        investments=investments,
        total_value=total_value,
        total_invested=total_invested,
        total_profit=total_profit,
        total_profit_percent=total_profit_percent,
        allocation=allocation,
        investment_summary=investment_summary,
        get_investment_summary=get_investment_summary)

# Цели
@app.route('/goals')
@login_required
@load_user_data_decorator
def goals_page(user_data, current_user):
    goals = user_data.get("goals", [])

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

    # Общая статистика
    total_target = sum(g.get("target", 0) for g in goals if isinstance(g, dict))
    total_saved = sum(g.get("saved", 0) for g in goals if isinstance(g, dict))

    return render_template(
        'goals.html',
        current_title="Цели",
        current_user=current_user,
        current_year=datetime.now().year,
        goals=goals,
        goals_sorted=goals_sorted,
        total_target=total_target,
        total_saved=total_saved
    )

@app.route('/add-goal')
@login_required
def add_goal_page():

    from datetime import datetime, timedelta
    default_deadline = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

    return render_template(
        'add_goal.html',
        current_title="Создать цель",
        current_user=get_current_user,
        current_year=datetime.now().year,
        default_deadline=default_deadline
    )

@app.route('/api/add-goal', methods=['POST'])
@login_required
@load_user_data_decorator
def api_add_goal(user_data, current_user):
    try:
        target = float(request.form.get("target", 0))
        saved_str = request.form.get("saved", "").strip()
        saved = float(saved_str) if saved_str else 0.0

        goal = {
            "id": len(user_data.get("goals", [])) + 1,
            "name": request.form.get("name", ""),
            "description": request.form.get("description", ""),
            "target": target,
            "saved": saved,
            "deadline": request.form.get("deadline", datetime.now().strftime("%Y-%m-%d")),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "progress": (saved / target * 100) if target > 0 else 0
        }
        if "goals" not in user_data:
            user_data["goals"] = []

        user_data["goals"].append(goal)
        save_user_data(current_user['id'], user_data)

        return redirect("/goals")

    except Exception as e:
        print(f"Ошибка при создании цели: {e}")
        return redirect("/add-goal")

@app.route('/api/goals/<int:goal_id>/add', methods=['POST'])
@login_required
@load_user_data_decorator
def api_add_to_goal(user_data, current_user, goal_id):
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
@login_required
@load_user_data_decorator
def api_delete_goal(user_data, current_user, goal_id):
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
@login_required
@load_user_data_decorator
def edit_goal_page(user_data, current_user):
    goal_id = int(request.args.get('id', 0))

    goal = None
    for g in user_data.get("goals", []):
        if isinstance(g, dict) and g.get("id") == goal_id:
            goal = g
            break

    if not goal:
        return redirect("/goals")

    return render_template(
        'edit_goal.html',  # Создадим этот шаблон позже
        current_title="Редактировать цель",
        current_user=current_user,
        current_year=datetime.now().year,
        goal=goal
    )

@app.route('/api/edit-goal', methods=['POST'])
@login_required
@load_user_data_decorator
def api_edit_goal(user_data, current_user):
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
                goal["progress"] = (saved / target * 100) if target > 0 else 0

                save_user_data(current_user['id'], user_data)
                return redirect("/goals")

        return redirect("/goals")

    except Exception as e:
        print(f"Ошибка при редактировании цели: {e}")
        return redirect("/edit-goal?id=" + request.form.get("id", ""))

@app.route('/reports')
@login_required
@load_user_data_decorator
def reports_page(user_data, current_user):
    transactions = user_data.get("transactions", [])
    investments = user_data.get("investments", [])
    goals = user_data.get("goals", [])

    # Получаем данные для отчетов
    monthly_data = get_monthly_summary(transactions)
    expense_categories = get_category_summary(transactions, "expense")
    income_categories = get_category_summary(transactions, "income")
    investment_summary = get_investment_summary(investments)

    # Общая статистика транзакций
    total_income = sum(t.get("amount", 0) for t in transactions if isinstance(t, dict) and t.get("amount", 0) > 0)
    total_expense = sum(abs(t.get("amount", 0)) for t in transactions if isinstance(t, dict) and t.get("amount", 0) < 0)
    total_balance = total_income - total_expense

    # Статистика целей
    total_goals_target = sum(g.get("target", 0) for g in goals if isinstance(g, dict))
    total_goals_saved = sum(g.get("saved", 0) for g in goals if isinstance(g, dict))
    goals_progress = (total_goals_saved / total_goals_target * 100) if total_goals_target > 0 else 0

    return render_template(
        'reports.html',
        current_title="Отчеты",
        current_user=current_user,
        current_year=datetime.now().year,
        transactions=transactions,
        investments=investments,
        goals=goals,
        monthly_data=monthly_data,
        expense_categories=expense_categories,
        income_categories=income_categories,
        investment_summary=investment_summary,
        total_income=total_income,
        total_expense=total_expense,
        total_balance=total_balance,
        total_goals_target=total_goals_target,
        total_goals_saved=total_goals_saved,
        goals_progress=goals_progress
    )
# СБРОС ДАННЫХ
@app.route('/reset-data')
@login_required
@load_user_data_decorator
def reset_data_page(user_data, current_user):
    """Страница подтверждения сброса данных"""
    transactions = user_data.get("transactions", [])
    investments = user_data.get("investments", [])
    goals = user_data.get("goals", [])

    # Подсчитываем статистику
    transactions_count = len(transactions)
    investments_count = len(investments)
    goals_count = len(goals)
    total_items = transactions_count + investments_count + goals_count

    return render_template(
        'reset_data.html',
        current_title="Сброс данных",
        current_user=current_user,
        current_year=datetime.now().year,
        transactions_count=transactions_count,
        investments_count=investments_count,
        goals_count=goals_count,
        total_items=total_items
    )


@app.route('/api/reset-data', methods=['POST'])
@login_required
def api_reset_data():
    """API для сброса всех данных"""
    try:
        new_data = create_default_data()
        current_user = get_current_user()
        if current_user:
            for i, user in enumerate(new_data["users"]):
                if user["username"] == "demo":
                    new_data["users"][i] = {
                        "id": current_user["id"],
                        "username": current_user["username"],
                        "password_hash": current_user.get("password_hash", ""),
                        "email": current_user.get("email", ""),
                        "created_at": current_user.get("created_at", datetime.now().strftime("%Y-%m-%d")),
                        "risk_profile": current_user.get("risk_profile", 2),
                        "transactions": [],  # Очищаем данные
                        "investments": [],
                        "goals": []
                    }
                    break
        save_data(new_data)
        session.clear()

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

#ЗАПУСК ПРИЛОЖЕНИЯ
if __name__ == '__main__':
    print("=" * 70)
    print(" Главная страница:      http://localhost:5000")
    print(" Транзакции:            http://localhost:5000/transactions")
    print(" Инвестиции:            http://localhost:5000/investments")
    print(" Цели:                  http://localhost:5000/goals")
    print(" Отчеты:                http://localhost:5000/reports")
    print(" Экспорт данных:        http://localhost:5000/export")


    # Проверяем и создаем файл данных
    if not os.path.exists(DATA_FILE):
        print(" Создаем файл данных...")
        save_data(create_default_data())

    app.run(debug=True, port=5000)