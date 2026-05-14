import json
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.conf import settings
from django.contrib.auth.models import User
from django.apps import apps as django_apps
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from apps.core.utils.license_service import LicenseService

UserLog = django_apps.get_model('authorize', 'UserLog')
UserAuth = django_apps.get_model('authorize', 'UserAuth')
IPBlacklist = django_apps.get_model('authorize', 'IPBlacklist')

@login_required(login_url='/login')
def ApiDashboardStats(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    # User count grouped by role or filtered by role
    role_filter = request.GET.get('role', 'all')
    user_roles_qs = UserAuth.objects.values('user_permission__name').annotate(count=Count('id')).order_by()
    users_by_role = {item['user_permission__name']: item['count'] for item in user_roles_qs if item['user_permission__name']}
    
    if role_filter != 'all':
        filtered_count = UserAuth.objects.filter(user_permission__name=role_filter).count()
        user_display_count = filtered_count
    else:
        user_display_count = User.objects.count()

    # Audio Plays filtering
    days = request.GET.get('play_audio_days', 'all')
    status = request.GET.get('play_audio_status', 'success')

    plays_query = UserLog.objects.filter(action='Play audio')
    
    if status != 'all':
        plays_query = plays_query.filter(status=status)
    
    if days != 'all':
        try:
            d = int(days)
            cutoff = timezone.now() - timedelta(days=d)
            plays_query = plays_query.filter(timestamp__gte=cutoff)
        except ValueError:
            pass
            
    total_plays = plays_query.count()

    # System Metrics (psutil)
    if _HAS_PSUTIL:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            disk = psutil.disk_usage('/')
            disk_info = {
                'driver': '/',
                'used': f"{disk.used / (1024**3):.2f} GB",
                'free': f"{disk.free / (1024**3):.2f} GB",
                'total': f"{disk.total / (1024**3):.2f} GB"
            }
        except Exception:
            cpu_percent = 0
            memory_percent = 0
            disk_info = {}
    else:
        cpu_percent = -1
        memory_percent = -1
        disk_info = {'error': 'psutil not installed'}

    # Licenses & Concurrency
    license_svc = LicenseService()
    license_data = license_svc.get_license_info() or {}
    active_user_count = license_svc.get_active_user_count()
    max_concurrent_users = license_data.get('features', {}).get('max_concurrent_users', 0)

    return JsonResponse({
        'users_by_role': users_by_role,
        'user_display_count': user_display_count,
        'total_plays': total_plays,
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'disk_info': disk_info,
        'license': license_data,
        'active_user_count': active_user_count,
        'max_concurrent_users': max_concurrent_users
    })

@login_required(login_url='/login')
def ApiDashboardAlarms(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    data = []
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Concurrent Users Check
    license_svc = LicenseService()
    active_count = license_svc.get_active_user_count()
    license_info = license_svc.get_license_info() or {}
    max_users = license_info.get('features', {}).get('max_concurrent_users', 0)
    
    if max_users > 0 and active_count > max_users:
        data.append({
            'id': 'concurrent_limit',
            'time': now_str,
            'event': 'Concurrent Users Exceeded',
            'message': f'Current active users ({active_count}) exceeds license limit ({max_users}).',
            'ip_address': '-',
            'user_id': None,
            'username': '-',
            'type': 'concurrent'
        })

    # 2. System Load Warnings
    if _HAS_PSUTIL:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        if cpu > 90 or mem > 90:
            data.append({
                'id': 'system_load',
                'time': now_str,
                'event': 'System Instability',
                'message': f'High system load detected: CPU {cpu}%, Memory {mem}%.',
                'ip_address': '-',
                'user_id': None,
                'username': '-',
                'type': 'system'
            })

    # 3. Security & Strange Error Logs
    # Exclude "Play audio" error logs and other non-critical logs as requested.
    alarms_qs = UserLog.objects.filter(
        (Q(status='error') & ~Q(action='Play audio')) | 
        Q(action__icontains='Blocked') |
        Q(action__icontains='Unauthorized') |
        Q(action__icontains='System Error')
    ).order_by('-timestamp')[:50]

    for a in alarms_qs:
        data.append({
            'id': a.id,
            'time': a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'event': a.action,
            'message': a.detail,
            'ip_address': a.ip_address or '-',
            'user_id': a.user.id if a.user else None,
            'username': a.user.username if a.user else '-',
            'type': 'log'
        })

    return JsonResponse({'alarms': data})

@login_required(login_url='/login')
def ApiDashboardActiveUsers(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    license_svc = LicenseService()
    user_ids = license_svc.get_active_user_ids()
    
    users = User.objects.filter(id__in=user_ids).only('id', 'username', 'email')
    user_map = {str(u.id): u for u in users}
    
    data = []
    for uid in user_ids:
        u = user_map.get(str(uid))
        if not u: continue
        
        # Get last login info from logs
        last_log = UserLog.objects.filter(user=u, action='Login', status='success').order_by('-timestamp').first()
        
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'ip_address': last_log.ip_address if last_log else '-',
            'login_time': last_log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if last_log else '-'
        })
        
    return JsonResponse({'users': data})

@csrf_exempt
@login_required(login_url='/login')
def ApiDashboardAction(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'kick_out':
                user_id = data.get('user_id')
                if user_id:
                    for ot in OutstandingToken.objects.filter(user_id=user_id):
                        BlacklistedToken.objects.get_or_create(token=ot)
                    return JsonResponse({'status': 'success', 'message': f'User {user_id} kicked out successfully'})
            
            elif action == 'block_ip':
                ip = data.get('ip_address')
                if ip and ip != '-':
                    IPBlacklist.objects.get_or_create(ip_address=ip, defaults={'reason': 'Blocked from Dashboard', 'created_by': request.user})
                    return JsonResponse({'status': 'success', 'message': f'IP {ip} blocked successfully'})
                return JsonResponse({'status': 'error', 'message': 'Invalid IP'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'error': 'Bad Request'}, status=400)
