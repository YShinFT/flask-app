from datetime import datetime

def format_currency(amount):

    return f"{amount:,.2f} ₽"

def format_date(date_str, format_from='%Y-%m-%d', format_to='%d.%m.%Y'):

    try:
        date_obj = datetime.strptime(date_str, format_from)
        return date_obj.strftime(format_to)
    except:
        return date_str

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

def generate_recommendations(investments, risk_profiles, risk_profile_id=2):
    """Генерация рекомендаций с передачей risk_profiles"""
    recommendations = []

    if not investments:
        recommendations.append({
            "type": "info",
            "title": "Начните инвестировать",
            "message": "Ваш портфель пуст. Начните с создания диверсифицированного портфеля.",
            "priority": "high"
        })
        return recommendations

    # Находим выбранный профиль риска из переданного списка
    selected_profile = None
    for profile in risk_profiles:  # ← risk_profiles ПЕРЕДАНО как параметр
        if isinstance(profile, dict) and profile.get("id") == risk_profile_id:
            selected_profile = profile
            break

    if not selected_profile:
        selected_profile = risk_profiles[1] if len(risk_profiles) > 1 else {
            "name": "Умеренный",
            "stocks_ratio": 50,
            "bonds_ratio": 40,
            "cash_ratio": 10
        }

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

def get_recent_transactions_table(transactions):
    if not transactions:
        return '''
        <div style="text-align: center; padding: 30px; color: #666;">
            <i class="fas fa-exchange-alt" style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;"></i>
            <p style="font-size: 16px;">Нет операций</p>
        </div>
        '''

    rows = ''
    for t in transactions:
        if not isinstance(t, dict):
            continue

        amount = t.get("amount", 0)
        sign = "+" if amount > 0 else ""

        # Обрезаем длинное описание на мобильных
        description = t.get('description', 'Без описания')
        if len(description) > 50:
            description = description[:47] + "..."

        rows += f'''
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #e0e0e0;">
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{description}</div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">
                    <span style="margin-right: 10px;">{t.get('date', 'Нет даты')}</span>
                    <span>•</span>
                    <span style="margin-left: 10px;">{t.get('category', 'Другое')}</span>
                </div>
            </div>
            <div style="font-weight: bold; color: {'#4CAF50' if amount > 0 else '#f44336'}; font-size: 16px; white-space: nowrap; margin-left: 10px;">
                {sign}{abs(amount):,.2f} ₽
            </div>
        </div>
        '''

    return f'''
    <div style="max-width: 100%; overflow: hidden;">
        {rows}
    </div>
    '''

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

def format_investment_html(investments):
    """Форматирование списка инвестиций в HTML"""
    if not investments:
        return '<p style="text-align: center; color: #666; padding: 20px;">Нет инвестиций</p>'

    html = ""
    for inv in investments:
        if isinstance(inv, dict):
            current_value = inv.get("current_value", inv.get("amount", 0))
            purchase_value = inv.get("amount", 0)
            profit = current_value - purchase_value
            profit_percent = (profit / purchase_value * 100) if purchase_value > 0 else 0

            html += f'''
            <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #e0e0e0;">
                <div>
                    <div style="font-weight: 500;">{inv.get('name', 'Без названия')}</div>
                    <div style="font-size: 12px; color: #666;">{inv.get('type', 'Акции')} • {format_date(inv.get('purchase_date', ''))}</div>
                </div>
                <div>
                    <div style="font-weight: bold; text-align: right;">{format_currency(current_value)}</div>
                    <div style="font-size: 12px; color: {'#4CAF50' if profit >= 0 else '#f44336'}; text-align: right;">
                        {'+' if profit >= 0 else ''}{format_currency(profit)} ({profit_percent:+.1f}%)
                    </div>
                </div>
            </div>
            '''
    return html