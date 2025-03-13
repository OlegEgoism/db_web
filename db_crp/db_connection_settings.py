from db_crp.models import ConnectingDB

from django.shortcuts import get_object_or_404


def get_db_connection_settings(db_id):
    """Настройки подключения к базе данных"""
    connection_info = get_object_or_404(ConnectingDB, id=db_id)
    return {
        'dbname': connection_info.name_db,
        'user': connection_info.user_db,
        'password': connection_info.get_decrypted_password(),
        'host': connection_info.host_db,
        'port': connection_info.port_db,
    }


