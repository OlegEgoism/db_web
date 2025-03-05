# from django.template.defaultfilters import register
#
#
# @register.filter
# def get_item(dictionary, key):
#     """Возвращает значение по ключу из словаря"""
#     return dictionary.get(key, None)



from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Возвращает значение по ключу из словаря"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, None)
    return None




# @register.filter
# def get_item(dictionary, key):
#     """Получает элемент словаря по ключу"""
#     return dictionary.get(key, None)
