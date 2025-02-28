from django.contrib.auth import login, logout
from .audit_views import user_register, create_audit_log
from .forms import CustomUserRegistrationForm
from django.shortcuts import render, redirect
from django.contrib import messages


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
