from datetime import datetime
from django.contrib.auth import login, logout
from django.utils import timezone
from django.utils.timezone import now
from .forms import CustomUserRegistrationForm
from django.shortcuts import render, redirect
from .models import Audit
from django.contrib import messages


def home(request):
    """Главная"""
    return render(request, 'home.html')


def register(request):
    """Регистрация пользователя"""
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Audit.objects.create(
                username=user.username,
                action_type='register',
                entity_type='user',
                entity_name=user.username,
                timestamp=now(),
                details=f"Пользователь {user.username} зарегистрирован, почта {user.email}, телефон {user.phone_number}."
            )
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
