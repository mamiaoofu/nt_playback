from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q

from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import re

from apps.core.model.authorize.models import UserLog
from apps.core.utils.permissions import get_user_actions
from apps.core.utils.permission_ids import PermissionIDs

def ApiGetUserLogs(request,type):
    try:
        type = str(type)
    except (ValueError, TypeError):
        return JsonResponse({'status': False, 'message': 'Invalid type'}, status=400)

    # permission check depending on log type
    if type == 'system':
        required_id = PermissionIDs.SYSTEM_LOG_ACCESS
    elif type == 'audit':
        required_id = PermissionIDs.AUDIT_LOG_ACCESS
    else:
        required_id = PermissionIDs.SYSTEM_LOG_ACCESS

    # superuser / ID=1 bypass
    if not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'id', None) == 1):
        user_actions = get_user_actions(request.user)
        if required_id not in user_actions:
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
    
    def _parse_date_param(val, is_end=False):
        if not val:
            return None
        # try Django's parse_datetime first
        dt = None
        try:
            dt = parse_datetime(val)
        except Exception:
            dt = None

        # fallback to common formats
        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(val, fmt)
                    break
                except Exception:
                    dt = None

        if dt is None:
            return None

        # If input was date-only like YYYY-MM-DD, adjust to start/end of day
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
            if is_end:
                dt = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
            else:
                dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0)

        if settings.USE_TZ and dt.tzinfo is None:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        return dt

    # base queryset and type filter
    # avoid N+1 queries on user access by selecting related user
    log_list = UserLog.objects.select_related('user').all()

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
        # allow comma-separated list of usernames from frontend (e.g. "snadmin,wisitp")
        try:
            names = [n.strip() for n in str(name).split(',') if n.strip()]
            if len(names) > 1:
                log_list = log_list.filter(user__username__in=names)
            else:
                log_list = log_list.filter(user__username=names[0])
        except Exception:
            log_list = log_list.filter(user__username=name)
    if username:
        log_list = log_list.filter(user__username__icontains=username)
    if full_name:
        log_list = log_list.filter(Q(user__first_name__icontains=full_name) | Q(user__last_name__icontains=full_name))    
    if action:
        # allow comma-separated list of actions (e.g. "Login,Play audio")
        try:
            acts = [a.strip() for a in str(action).split(',') if a.strip()]
            if len(acts) > 1:
                log_list = log_list.filter(action__in=acts)
            else:
                log_list = log_list.filter(action__icontains=acts[0])
        except Exception:
            log_list = log_list.filter(action__icontains=action)
    if status:
        log_list = log_list.filter(status__icontains=status)
    if description:
        log_list = log_list.filter(detail__icontains=description)
    if ip_address:
        log_list = log_list.filter(ip_address__icontains=ip_address)
    # parse start/end parameters with sensible fallbacks and inclusive end-date
    dt_start = _parse_date_param(start_date, is_end=False) if start_date else None
    dt_end = _parse_date_param(end_date, is_end=True) if end_date else None

    if dt_start and dt_end:
        log_list = log_list.filter(timestamp__gte=dt_start, timestamp__lte=dt_end)
    elif dt_start:
        log_list = log_list.filter(timestamp__gte=dt_start)
    elif dt_end:
        log_list = log_list.filter(timestamp__lte=dt_end)
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

    # Sorting support: read sort params (e.g., sort[0][field]=action, sort[0][dir]=desc)
    sort_field = request.POST.get("sort[0][field]") or request.GET.get("sort[0][field]")
    sort_dir = (request.POST.get("sort[0][dir]") or request.GET.get("sort[0][dir]") or "asc").lower()
    if sort_field:
        field_map = {
            "username": "user__username",
            "action": "action",
            "status": "status",
            "detail": "detail",
            "ip_address": "ip_address",
            "timestamp": "timestamp",
            "client_type": "client_type",
            # full_name handled specially
            "full_name": None,
        }
        mapped = field_map.get(sort_field)
        try:
            if sort_field == "full_name":
                # order by first_name then last_name
                if sort_dir == "desc":
                    log_list = log_list.order_by("-user__first_name", "-user__last_name")
                else:
                    log_list = log_list.order_by("user__first_name", "user__last_name")
            elif mapped:
                prefix = "-" if sort_dir == "desc" else ""
                log_list = log_list.order_by(prefix + mapped)
        except Exception:
            pass

    # Pagination (select_related already applied)
    log_page = log_list[start:start + length]

    data = []
    for idx, log in enumerate(log_page, start=start+1):
        # format timestamp respecting TIME_ZONE / USE_TZ
        if log.timestamp:
            try:
                ts = timezone.localtime(log.timestamp) 
                ts_str = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                try:
                    ts_str = str(log.timestamp)
                except Exception:
                    ts_str = "-"
        else:
            ts_str = "-"

        data.append({
            "no": idx,
            "username": str(log.user) if log.user else "-",
            "full_name": f"{log.user.first_name} {log.user.last_name}" if log.user else "-",
            "action": str(log.action) if log.action else "-",
            "status": str(log.status) if log.status else "-",
            "detail": str(log.detail) if log.detail else "-",
            "ip_address": str(log.ip_address) if log.ip_address else "-",
            "detail": str(log.detail) if log.detail else "-",
            "timestamp": ts_str,
            "client_type": str(log.client_type) if log.client_type else "-",
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })

def ApiGetActionOptions(request):
    try:
        log_type = request.GET.get('type')
        
        audit_actions = {
            'Login', 'Logout', 'Playback Audio Records', 'Download Audio Records', 'Save as Audio Index',
            'Create My Favorite', 'Edit My Favorite', 'Delete My Favorite', 'Add Column Audio Records',
            'Edit Column Audio Records', 'Delete Column Audio Records', 'Enable Column Audio Records',
            'Disable Column Audio Records', 'Add User', 'Edit User', 'Delete User', 'Change User Status',
            'Reset User Password', 'Save as User Index', 'Add Group', 'Edit Group', 'Delete Group',
            'Add Team', 'Edit Team', 'Delete Team', 'Edit Base Role', 'Add Custom Role', 'Edit Custom Role',
            'Delete Custom Role', 'Save as System Log', 'Save as Audit Log', 'Create Delegate',
            'Playback Delegate File', 'Download Delegate File', 'Change Delegate Status', 'Create Ticket',
            'Playback Ticket File', 'Download Ticket File', 'Change Ticket Status', 'Save as Ticket History',
            'Ticket Resent', 'Ticket Send Mail', 'Ticket Copy Form', 'Download Player', 'User Change Password'
        }
        
        excluded_retention_actions = [
            'Save and Run Schedule Retention',
            'Stop Schedule Retention',
            'Run Schedule Retention',
            'Complete Soft Delete Schedule Retention',
            'Complete Delete Schedule Retention',
            'Restore Data Schedule Retention',
            'Complete Soft Delete Immediately Retention',
            'Complete Delete Immediately Retention',
            'Restore Data Immediately Retention',
        ]
        
        # Start with all distinct actions
        actions_qs = UserLog.objects.exclude(action__in=excluded_retention_actions).values_list('action', flat=True).order_by('action').distinct()
        
        # If type is specified, filter actions
        if log_type == 'audit':
            actions_qs = actions_qs.filter(action__in=audit_actions)
        elif log_type == 'system':
            # System actions are those not in audit_actions or having errors
            actions_qs = UserLog.objects.filter(
                Q(status='error') | (Q(status='success') & ~Q(action__in=audit_actions))
            ).exclude(action__in=excluded_retention_actions).values_list('action', flat=True).order_by('action').distinct()
            
        # Use a set to remove any duplicates that might have different leading/trailing whitespaces
        unique_actions = set()
        for a in actions_qs:
            if a:
                val = a.strip()
                if val == 'Save As Retention Log':
                    val = 'Save as Retention Log'
                unique_actions.add(val)
                
        actions = list(unique_actions)
        actions.sort()
        return JsonResponse({'status': True, 'actions': actions})
    except Exception as e:
        return JsonResponse({'status': False, 'message': str(e)}, status=500)
