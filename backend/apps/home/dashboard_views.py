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
from django.apps import apps
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

UserLog = apps.get_model('authorize', 'UserLog')
UserAuth = apps.get_model('authorize', 'UserAuth')
IPBlacklist = apps.get_model('authorize', 'IPBlacklist')

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

    # Licenses
    license_data = {}
    license_path = os.path.join(settings.BASE_DIR, 'license', 'license.json')
    if os.path.exists(license_path):
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_data = json.load(f)
        except Exception:
            pass

    return JsonResponse({
        'users_by_role': users_by_role,
        'user_display_count': user_display_count,
        'total_plays': total_plays,
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'disk_info': disk_info,
        'license': license_data
    })

@login_required(login_url='/login')
def ApiDashboardAlarms(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    # Queries logs that look suspicious
    alarms = UserLog.objects.filter(
        Q(action__icontains='Failed login') | 
        Q(status__icontains='error') | 
        Q(action__icontains='Blocked') |
        Q(action__icontains='Unauthorized')
    ).order_by('-timestamp')[:50]

    data = []
    for a in alarms:
        data.append({
            'id': a.id,
            'time': a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'event': a.action,
            'message': a.detail,
            'ip_address': a.ip_address or '-',
            'user_id': a.user.id if a.user else None,
            'username': a.user.username if a.user else '-'
        })

    return JsonResponse({'alarms': data})

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
