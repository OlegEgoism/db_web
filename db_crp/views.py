from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from .audit_views import user_register, create_audit_log, logout_user_success, export_audit_log_success
from .forms import CustomUserRegistrationForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
import xlsxwriter
from django.http import HttpResponse
from .models import Audit

User = get_user_model()


def home(request):
    """Главная"""
    return render(request, 'home.html')


def register(request):
    """Регистрация пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            message = user_register(user.username, user.email, user.phone_number)
            messages.success(request, message)
            create_audit_log(user_requester, 'register', 'user', user.username, message)
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле {form.fields[field].label}: {error}")
    else:
        form = CustomUserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Выход пользователя"""
    logout(request)
    return redirect('home')


def audit_log(request):
    """Аудит приложения"""
    action_type = request.GET.get("action_type", "")
    entity_type = request.GET.get("entity_type", "")
    username = request.GET.get("username", "")
    search_query = request.GET.get("search", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    page_number = request.GET.get("page", 1)
    audit_entries = Audit.objects.all()
    if action_type:
        audit_entries = audit_entries.filter(action_type=action_type)
    if entity_type:
        audit_entries = audit_entries.filter(entity_type=entity_type)
    if username:
        audit_entries = audit_entries.filter(username=username)
    if search_query:
        audit_entries = audit_entries.filter(
            Q(entity_name__icontains=search_query) |
            Q(details__icontains=search_query)
        )
    if start_date:
        start_date_parsed = parse_date(start_date)
        if start_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__gte=start_date_parsed)
    if end_date:
        end_date_parsed = parse_date(end_date)
        if end_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__lte=end_date_parsed)
    paginator = Paginator(audit_entries, 5)
    page_obj = paginator.get_page(page_number)
    action_choices = Audit.ACTION_TYPES
    entity_choices = Audit.ENTITY_TYPES
    usernames = Audit.objects.values_list("username", flat=True).distinct()
    return render(request, "audit/audit_log.html", {
        "page_obj": page_obj,
        "action_choices": action_choices,
        "entity_choices": entity_choices,
        "usernames": usernames,
        "selected_action": action_type,
        "selected_entity": entity_type,
        "selected_user": username,
        "search_query": search_query,
        "start_date": start_date,
        "end_date": end_date,
    })


def export_audit_log(request):
    """Экспорт данных журнала аудита в Excel"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    action_type = request.GET.get("action_type", "")
    entity_type = request.GET.get("entity_type", "")
    username = request.GET.get("username", "")
    search_query = request.GET.get("search", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    audit_entries = Audit.objects.all()
    if action_type:
        audit_entries = audit_entries.filter(action_type=action_type)
    if entity_type:
        audit_entries = audit_entries.filter(entity_type=entity_type)
    if username:
        audit_entries = audit_entries.filter(username=username)
    if search_query:
        audit_entries = audit_entries.filter(
            Q(entity_name__icontains=search_query) |
            Q(details__icontains=search_query)
        )
    if start_date:
        start_date_parsed = parse_date(start_date)
        if start_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__gte=start_date_parsed)
    if end_date:
        end_date_parsed = parse_date(end_date)
        if end_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__lte=end_date_parsed)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=audit_log_filtered.xlsx'
    workbook = xlsxwriter.Workbook(response, {'in_memory': True})
    worksheet = workbook.add_worksheet('Audit Log')
    if worksheet:
        message = export_audit_log_success(user_requester)
        messages.success(request, message)
        create_audit_log(user_requester, 'download', 'audit', user_requester, message)
    headers = ["Дата", "Пользователь", "Действие", "Объект", "Название", "Информация"]
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)
    for row_num, entry in enumerate(audit_entries, start=1):
        row_data = [
            entry.timestamp.replace(tzinfo=None) if entry.timestamp else "",
            entry.username,
            entry.get_action_type_display(),
            entry.get_entity_type_display(),
            entry.entity_name or "",
            entry.details or ""
        ]
        for col_num, cell_value in enumerate(row_data):
            worksheet.write(row_num, col_num, str(cell_value) if cell_value else "")
    workbook.close()
    return response


def session_list(request):
    """Список сессий пользователей"""
    search_query = request.GET.get("search", "")
    page_number = request.GET.get("page", 1)
    active_sessions = Session.objects.filter(expire_date__gte=now())
    session_data = []
    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        session_data.append({
            "session_key": session.session_key,
            "username": user.username if user else "Аноним",
            "last_login": user.last_login if user else "—",
            "expire_date": session.expire_date,
            "is_superuser": user.is_superuser if user else False,
        })
    if search_query:
        session_data = [s for s in session_data if search_query.lower() in s["username"].lower()]
    paginator = Paginator(session_data, 5)
    page_obj = paginator.get_page(page_number)
    return render(request, "audit/session_list.html", {
        "page_obj": page_obj,
        "search_query": search_query
    })


def logout_user(request, session_id):
    """Деактивация сессии пользователя"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    session = Session.objects.filter(session_key=session_id).first()
    if session:
        session_data = session.get_decoded()
        user_id = session_data.get('_auth_user_id')
        user_logout = User.objects.filter(id=user_id).first()
        if user_logout:
            user_logout = user_logout.username
            session.delete()
            message = logout_user_success(user_logout, user_requester)
            messages.success(request, message)
            create_audit_log(user_requester, 'delete', 'session', user_requester, message)
    return redirect('session_list')
