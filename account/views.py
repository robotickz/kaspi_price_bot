from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from .models import Company


@permission_required("account.add_employee", login_url="/account/login/")
def register_view(request):
    if request.method == 'POST':
        user = User.objects.create_user(
            request.POST.get('email'),
            request.POST.get('email'),
            request.POST.get('password'),
            first_name=request.POST.get('name')
        )
        user.refresh_from_db()
        user.employee.phone = request.POST.get('phone')
        user.save()
        company = Company.objects.create(name=request.POST.get('company_name'))
        company.employees.add(user.employee)
        company.save()
        user = authenticate(username=user.username, password=request.POST.get('password'))
        login(request, user)
        return redirect('core:index-view')
    return render(request, 'account/register.html', {})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST.get('email'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('core:index-view')
    return render(request, 'account/login.html', {})


def logout_view(request):
    logout(request)
    return redirect('core:index-view')


def profile_view(request):
    return render(request, 'account/profile.html', {})
