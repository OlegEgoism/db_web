from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from .audit_views import create_audit_log, logout_user_success, export_audit_log_success, project_settings_success
from .forms import SettingsProjectForm
from django.shortcuts import render, redirect
from django.contrib import messages
import xlsxwriter
from django.http import HttpResponse
from .models import Audit, SettingsProject

User = get_user_model()


@login_required
def audit_log(request):
    """Аудит приложения"""
    pagination_size = SettingsProject.objects.first().pagination_size if SettingsProject.objects.exists() else 20
    action_type = request.GET.get("action_type", "")
    entity_type = request.GET.get("entity_type", "")
    username = request.GET.get("username", "")
    search_query = request.GET.get("search", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    page_number = request.GET.get("page", 1)
    audit_entries = Audit.objects.all().order_by('-timestamp')
    if action_type:
        audit_entries = audit_entries.filter(action_type=action_type)
    if entity_type:
        audit_entries = audit_entries.filter(entity_type=entity_type)
    if username:
        audit_entries = audit_entries.filter(username=username)
    if search_query:
        audit_entries = audit_entries.filter(Q(entity_name__icontains=search_query) | Q(details__icontains=search_query))
    if start_date:
        start_date_parsed = parse_date(start_date)
        if start_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__gte=start_date_parsed)
    if end_date:
        end_date_parsed = parse_date(end_date)
        if end_date_parsed:
            audit_entries = audit_entries.filter(timestamp__date__lte=end_date_parsed)
    paginator = Paginator(audit_entries, pagination_size)
    page_obj = paginator.get_page(page_number)
    action_choices = Audit.ACTION_TYPES
    entity_choices = Audit.ENTITY_TYPES
    usernames = Audit.objects.values_list("username", flat=True).distinct()
    return render(request, "settings/audit_log.html", {
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


@login_required
def audit_log_export(request):
    """Аудит приложения экспорт в Excel"""
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
        audit_entries = audit_entries.filter(Q(entity_name__icontains=search_query) | Q(details__icontains=search_query))
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
        create_audit_log(user_requester, 'download', 'settings', user_requester, message)
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


@login_required
def settings_info(request):
    """Настройки"""
    return render(request, "settings/settings.html")


@login_required
def settings_project(request):
    """Настройки проекта"""
    user_requester = request.user.username if request.user.is_authenticated else "Аноним"
    settings_instance = SettingsProject.objects.first()
    if request.method == "POST":
        form = SettingsProjectForm(request.POST, instance=settings_instance)
        if form.is_valid():
            form.save()
            pagination_size = form.cleaned_data["pagination_size"]
            send_email = form.cleaned_data["send_email"]
            message = project_settings_success(user_requester, pagination_size, send_email)
            messages.success(request, message)
            create_audit_log(user_requester, 'update', 'settings', user_requester, message)
            return redirect('settings_info')
    else:
        form = SettingsProjectForm(instance=settings_instance)
    return render(request, "settings/settings_project.html", {"form": form})


@login_required
def session_list(request):
    """Список сессий пользователей"""
    pagination_size = SettingsProject.objects.first().pagination_size if SettingsProject.objects.exists() else 20
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
            "email": user.email if user else "—",
            "last_login": user.last_login if user else "—",
            "expire_date": session.expire_date,
            "is_superuser": user.is_superuser if user else False,
        })
    if search_query:
        session_data = [s for s in session_data if search_query.lower() in s["username"].lower()]
    paginator = Paginator(session_data, pagination_size)
    page_obj = paginator.get_page(page_number)
    return render(request, "settings/session_list.html", {
        "page_obj": page_obj,
        "search_query": search_query
    })


@login_required
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
