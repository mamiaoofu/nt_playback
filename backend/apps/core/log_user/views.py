# apps/home/views.py
from django.shortcuts import render, redirect
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# from apps.page_notfound.views import page_not_found
from utils.function import BaseListAPIView,PageNumberPagination
from django.db.models import Q
from django.http import JsonResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.http import JsonResponse
import os
import subprocess
from datetime import datetime, timedelta
from django.contrib.auth.models import User

# models
from apps.model_center.authorize.models import UserAuth,MainDatabase
from apps.model_center.authorize.models import UserLog,UserProfile
from apps.core.utils.permissions import get_user_actions, require_action
from apps.core.utils.permission_ids import PermissionIDs
#serializer
from apps.model_center.authorize.serializers import MainDatabaseSerializer


class NoLimitPagination(PageNumberPagination):
    page_size = 1000  

def page_not_found(request, exception=None):
    return render(request, 'page_notfound/index.html', status=404)

def check_permission(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            user_auth = UserAuth.objects.filter(user=user).first()
            if user_auth and not user_auth.status:
                return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required(login_url='/login')
@require_action(PermissionIDs.SYSTEM_LOG_ACCESS, PermissionIDs.AUDIT_LOG_ACCESS)
def index(request, type):
    template = 'default/layout-leftbar.html'
    title = ''

    users = User.objects.filter(userlog__isnull=False).distinct()
    if type == 'audit':
        title = "Audit log"
        user_log = UserLog.objects.filter(status='success')
    elif type == 'system':
        title = "System log"
    

    context = {
        'template': template,
        'title': title,
        'users': users,
    }
    return render(request, 'log_user/index.html', context)

@login_required(login_url='/login')
@require_action(PermissionIDs.SYSTEM_LOG_ACCESS, PermissionIDs.AUDIT_LOG_ACCESS)
def get_log(request,type):
    # permission check based on type
    required_action_id = PermissionIDs.SYSTEM_LOG_ACCESS if type == 'system' else PermissionIDs.AUDIT_LOG_ACCESS
    user_actions = get_user_actions(request.user)
    if required_action_id not in user_actions:
        return JsonResponse({'detail': 'Access Denied'}, status=403)
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "").strip()
    
    # log_list = Viewlog.objects.all()
    # ฟิลเตอร์จาก request.form หรือ request.GET
    name = request.POST.get("name") or request.GET.get("name")
    username = request.POST.get("username") or request.GET.get("username")  
    full_name = request.POST.get("full_name") or request.GET.get("full_name")
    action = request.POST.get("action") or request.GET.get("action")
    status = request.POST.get("status") or request.GET.get("status")
    description = request.POST.get("detail") or request.GET.get("detail") 
    ip_address = request.POST.get("ip_address") or request.GET.get("ip_address")
    start_date = request.POST.get("start_date") or request.GET.get("start_date")
    end_date = request.POST.get("end_date") or request.GET.get("end_date")
    client_type = request.POST.get("client_type") or request.GET.get("client_type")
    
    # base queryset and type filter
    log_list = UserLog.objects.all()

    audit_actions = {
        'Login',
        'Logout',
        'Playback Audio Records',
        'Download Audio Records',
        'Save as Audio Index',
        'Create My Favorite',
        'Edit My Favorite',
        'Delete My Favorite',
        'Add Column Audio Records',
        'Edit Column Audio Records',
        'Delete Column Audio Records',
        'Enable Column Audio Records',
        'Disable Column Audio Records',
        'Add User',
        'Edit User',
        'Delete User',
        'Change User Status',
        'Reset User Password',
        'Save as User Index',
        'Add Group',
        'Edit Group',
        'Delete Group',
        'Add Team',
        'Edit Team',
        'Delete Team',
        'Edit Base Role',
        'Add Custom Role',
        'Edit Custom Role',
        'Delete Custom Role',
        'Save as System Log',
        'Save as Audit Log',
        'Create Delegate',
        'Playback Delegate File',
        'Download Delegate File',
        'Change Delegate Status',
        'Create Ticket',
        'Playback Ticket File',
        'Download Ticket File',
        'Change Ticket Status',
        'Save as Ticket History',
        'Ticket Resent',
        'Ticket Send Mail',
        'Ticket Copy Form',
        'Download Player',
        'User Change Password'
    }

    if type == 'system':
        log_list = log_list.filter(
            Q(status__in=['error', 'failed', 'fail', 'warning', 'ERROR', 'FAILED', 'FAIL', 'WARNING']) |
            (Q(status__in=['success', 'SUCCESS']) & ~Q(action__in=audit_actions))
        )
    elif type == 'audit':
        log_list = log_list.filter(status__in=['success', 'SUCCESS'], action__in=audit_actions)

    # total before applying filters (for DataTables recordsTotal)
    records_total = log_list.count()

    # apply explicit filters from form
    if name:
        log_list = log_list.filter(user__username=name)
    if username:
        log_list = log_list.filter(user__username__icontains=username)
    if full_name:
        log_list = log_list.filter(Q(user__first_name__icontains=full_name) | Q(user__last_name__icontains=full_name))    
    if action:
        log_list = log_list.filter(action__icontains=action)
    if status:
        log_list = log_list.filter(status__icontains=status)
    if description:
        log_list = log_list.filter(detail__icontains=description)
    if ip_address:
        log_list = log_list.filter(ip_address__icontains=ip_address)
    if start_date:
        log_list = log_list.filter(timestamp__gte=start_date)
    if end_date:
        log_list = log_list.filter(timestamp__lte=end_date)
    if client_type:
        log_list = log_list.filter(client_type__icontains=client_type)

    # support comma-separated search terms across multiple columns
    if search_value:
        tokens = [t.strip() for t in search_value.split(',') if t.strip()]
        if tokens:
            q_search = Q()
            for tok in tokens:
                q_tok = (Q(user__username__icontains=tok) |
                         Q(user__first_name__icontains=tok) |
                         Q(user__last_name__icontains=tok) |
                         Q(action__icontains=tok) |
                         Q(detail__icontains=tok) |
                         Q(ip_address__icontains=tok) |
                         Q(client_type__icontains=tok))
                q_search &= q_tok
            log_list = log_list.filter(q_search)

    # records after filtering
    records_filtered = log_list.count()

    # Pagination
    log_page = log_list[start:start + length]

    data = []
    for idx, log in enumerate(log_page, start=start+1):
        data.append({
            "no": idx,
            "username": str(log.user) if log.user else "-",
            "full_name": f"{log.user.first_name} {log.user.last_name}" if log.user else "-",
            "action": str(log.action) if log.action else "-",
            "status": str(log.status) if log.status else "-",
            "detail": str(log.detail) if log.detail else "-",
            "ip_address": str(log.ip_address) if log.ip_address else "-",
            "detail": str(log.detail) if log.detail else "-",
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "-",
            "client_type": str(log.client_type) if log.client_type else "-",
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })
