from functools import wraps
from flask import redirect, session


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


def load_user_data_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import get_current_user, load_user_data

        current_user = get_current_user()
        if not current_user:
            return redirect('/login')

        user_data = load_user_data(current_user['id'])
        if not user_data:
            return redirect('/login')

        # ИСПРАВЛЕНО: передаем оба параметра
        return f(*args, **kwargs, user_data=user_data, current_user=current_user)

    return decorated_function