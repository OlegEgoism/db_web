def messages_delete_user_error(username):
    return f"Неудачная попытка при удалении пользователя '{username}' из базы данных, пользователь не может быть удален, так как существуют зависимые объекты в базе данных."


def messages_delete_user_success(username):
    return f"Пользователь '{username}' был удален из базы данных."


def messages_delete_user_email(username, user_email):
    return f"Уведомление об удалении аккаунта пользователя '{username}' из базы данных отправлено на почту'{user_email}'."
