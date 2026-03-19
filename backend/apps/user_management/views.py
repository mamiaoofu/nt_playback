# apps/home/views.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction, DatabaseError,IntegrityError
from django.db.models import Q
import re
from django.contrib import messages
from apps.core.utils.function import create_user_log
import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
import pytz

# models
from apps.core.model.authorize.models import MainDatabase,UserAuth,UserProfile,Department,MainDatabase,UserGroup,UserTeam,UserLog


from apps.configuration.models import UserPermission,UserPermissionDetail
from apps.core.utils.permissions import require_action, get_user_actions

#serializer
from apps.core.model.authorize.serializers import UserProfileSerializer,DepartmentSerializer,UserGroupSerializer,UserTeamSerializer

from django.contrib.auth import get_user_model

User = get_user_model()

@login_required(login_url='/login')
@require_action('User Management','User Logs')
def ApiGetUserAll(request):
    try:
        users = User.objects.all().values('id', 'username', 'first_name', 'last_name', 'email').order_by('username')
        user_list = list(users)
        return JsonResponse({'status': 'success', 'data': user_list})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/login')
@require_action('User Management','User Logs')
def ApiGetUser(request):
    # prepare base query
    qs = UserProfile.objects.exclude(user__id=1).select_related('user', 'team')

    user_auths = UserAuth.objects.filter(
        allow=True,
        user_permission__isnull=False
    ).select_related('user', 'maindatabase', 'user_permission')

    auth_map = {}
    for auth in user_auths:
        auth_map.setdefault(auth.user_id, []).append(auth)

    main_db_ids = set(MainDatabase.objects.filter(status=True).values_list('id', flat=True))

    # apply explicit filters from query params
    # user: comma-separated user ids or usernames
    user_param = (request.GET.get('user') or '').strip()
    if user_param:
        parts = [p.strip() for p in user_param.split(',') if p.strip()]
        ids = []
        names = []
        for p in parts:
            if p.isdigit():
                try:
                    ids.append(int(p))
                except Exception:
                    names.append(p)
            else:
                names.append(p)
        if ids and names:
            qs = qs.filter(Q(user__id__in=ids) | Q(user__username__in=names))
        elif ids:
            qs = qs.filter(user__id__in=ids)
        elif names:
            qs = qs.filter(user__username__in=names)

    # create_by: can be username or 'First Last' string
    create_by_param = (request.GET.get('create_by') or '').strip()
    if create_by_param:
        tokens = [t for t in re.split(r'[\s]+', create_by_param) if t]
        if len(tokens) >= 2:
            # try to match both first and last name
            fn = tokens[0]
            ln = ' '.join(tokens[1:])
            qs = qs.filter(Q(create_by__first_name__icontains=fn) & Q(create_by__last_name__icontains=ln) | Q(create_by__username__iexact=create_by_param))
        else:
            qs = qs.filter(Q(create_by__username__iexact=create_by_param) | Q(create_by__first_name__icontains=create_by_param) | Q(create_by__last_name__icontains=create_by_param))

    # start_date / end_date filter: expected format 'YYYY-MM-DD HH:MM'
    start_param = (request.GET.get('start_date') or '').strip()
    end_param = (request.GET.get('end_date') or '').strip()
    if start_param or end_param:
        try:
            tz = timezone.get_current_timezone() or pytz.UTC
        except Exception:
            tz = pytz.UTC
        try:
            if start_param:
                start_dt = datetime.strptime(start_param, '%Y-%m-%d %H:%M')
                start_dt = timezone.make_aware(start_dt, timezone=tz)
                qs = qs.filter(create_at__gte=start_dt)
            if end_param:
                end_dt = datetime.strptime(end_param, '%Y-%m-%d %H:%M')
                # include the whole minute by setting seconds to 59
                end_dt = end_dt.replace(second=59)
                end_dt = timezone.make_aware(end_dt, timezone=tz)
                qs = qs.filter(create_at__lte=end_dt)
        except Exception:
            pass

    # apply search filter if provided (DataTables style: search[value])
    search_term = (request.GET.get('search[value]') or request.GET.get('search') or '').strip()
    if search_term:
        # split on commas first (support multi-value like "dbname,0202020202")
        tokens = [t.strip() for t in search_term.split(',') if t.strip()]
        # primary search term (use first token if present to avoid trailing-comma issues)
        search_primary = tokens[0] if tokens else search_term
        base_q = (
            Q(user__username__icontains=search_primary)
            | Q(user__first_name__icontains=search_primary)
            | Q(user__last_name__icontains=search_primary)
            | Q(user__email__icontains=search_primary)
            | Q(phone__icontains=search_primary)
            | Q(team__name__icontains=search_primary)
            | Q(team__user_group__group_name__icontains=search_primary)
            | Q(user_code__icontains=search_primary)
            | Q(user__userauth__maindatabase__database_name__icontains=search_primary)
            | Q(user__userauth__user_permission__name__icontains=search_primary)
            | Q(create_by__username__icontains=search_primary)
            | Q(create_by__first_name__icontains=search_primary)
            | Q(create_by__last_name__icontains=search_primary)
        )

        # detect date-like tokens and allow matching against create_at date
        # Support: full dates, year-only (2026), day-only (12),
        # and year+month pairs from token sequences (e.g., '2026 03' or '03 2026' -> March 2026)
        date_q = None
        i = 0
        while i < len(tokens):
            t = tokens[i]
            # try year-month (YYYY MM) where next token is month
            if t.isdigit() and len(t) == 4:
                try:
                    year = int(t)
                    next_t = tokens[i+1] if i+1 < len(tokens) else None
                    if next_t and next_t.isdigit():
                        m = int(next_t)
                        if 1 <= m <= 12:
                            q = Q(create_at__year=year, create_at__month=m)
                            date_q = q if date_q is None else date_q | q
                            i += 2
                            continue
                except Exception:
                    pass

            # try month-year (MM YYYY)
            if t.isdigit() and 1 <= len(t) <= 2:
                try:
                    m = int(t)
                    next_t = tokens[i+1] if i+1 < len(tokens) else None
                    if next_t and next_t.isdigit() and len(next_t) == 4:
                        year = int(next_t)
                        if 1 <= m <= 12:
                            q = Q(create_at__year=year, create_at__month=m)
                            date_q = q if date_q is None else date_q | q
                            i += 2
                            continue
                except Exception:
                    pass

            # single numeric token: treat as day or year
            if t.isdigit():
                try:
                    n = int(t)
                    if 1 <= n <= 31:
                        q = Q(create_at__day=n)
                        date_q = q if date_q is None else date_q | q
                    if len(t) == 4 and 1900 <= n <= 9999:
                        q = Q(create_at__year=n)
                        date_q = q if date_q is None else date_q | q
                except Exception:
                    pass
                i += 1
                continue

            # try parsing token as full date (if token wasn't split by separators)
            parsed = False
            for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d', '%d/%m/%Y'):
                try:
                    dt = datetime.strptime(t, fmt)
                    q = Q(create_at__date=dt.date())
                    date_q = q if date_q is None else date_q | q
                    parsed = True
                    break
                except Exception:
                    continue
            if parsed:
                i += 1
                continue

            i += 1

        if date_q:
            base_q = base_q | date_q

        # detect if the search term or its tokens match any MainDatabase name
        # Use normalized comparison (remove non-alphanumerics) to avoid mismatches like 'v.6.10' vs 'v6.10'
        matching_db_ids = []
        try:
            # quick DB-side contains check first
            if search_term:
                matching_db_ids = list(MainDatabase.objects.filter(database_name__icontains=search_term).values_list('id', flat=True))
        except Exception:
            matching_db_ids = []

        if not matching_db_ids:
            try:
                # normalize function: remove non-alphanumeric and lowercase
                def _norm(s):
                    return re.sub(r'[^0-9A-Za-z]+', '', (s or '')).lower()

                norm_search = _norm(search_term)
                dbs = list(MainDatabase.objects.all())
                # try matching normalized full search term inside normalized db name
                if norm_search:
                    for d in dbs:
                        nd = _norm(getattr(d, 'database_name', '') or '')
                        if norm_search and nd and norm_search in nd:
                            matching_db_ids.append(d.id)

                # fallback: require all normalized tokens present in normalized db name
                if not matching_db_ids and tokens:
                    norm_tokens = [ _norm(t) for t in tokens if t and _norm(t) ]
                    if norm_tokens:
                        for d in dbs:
                            nd = _norm(getattr(d, 'database_name', '') or '')
                            if nd and all(nt in nd for nt in norm_tokens):
                                matching_db_ids.append(d.id)
            except Exception:
                matching_db_ids = []

        db_strict_q = None
        if matching_db_ids:
            db_strict_q = Q(user__userauth__maindatabase__id__in=matching_db_ids)
            try:
                # apply strict DB filter immediately so later OR-combinations only consider matching DB rows
                qs = qs.filter(db_strict_q).distinct()
                # clear db_strict_q so we don't AND it again later
                db_strict_q = None
            except Exception:
                pass

        # detect status tokens using concise regex (matches prefixes like 'ac' or 'in')
        status_value = None
        status_tokens = set()
        try:
            for t in tokens:
                lower = (t or '').lower()
                if re.match(r'^(ac|act|active|a|actv)', lower):
                    status_value = True
                    status_tokens.add(t)
                    continue
                if re.match(r'^(in|inactive|i|inact)', lower):
                    status_value = False
                    status_tokens.add(t)
                    continue
        except Exception:
            status_tokens = set()

        applied_status_only = False

        # build per-token queries (each token must match somewhere) similar to ApiGetTicketHistory
        if len(tokens) > 1:
            per_token_qs = []
            for t in tokens:
                if not t:
                    continue
                # skip tokens that were used solely as status filters
                if t in status_tokens:
                    continue
                tq = (
                    Q(user__username__icontains=t)
                    | Q(user__first_name__icontains=t)
                    | Q(user__last_name__icontains=t)
                    | Q(user__email__icontains=t)
                    | Q(phone__icontains=t)
                    | Q(team__name__icontains=t)
                    | Q(team__user_group__group_name__icontains=t)
                    | Q(user_code__icontains=t)
                    | Q(user__userauth__maindatabase__database_name__icontains=t)
                    | Q(user__userauth__user_permission__name__icontains=t)
                    | Q(create_by__username__icontains=t)
                    | Q(create_by__first_name__icontains=t)
                    | Q(create_by__last_name__icontains=t)
                )
                per_token_qs.append(tq)

            # combine token queries with AND so all tokens must match somewhere
            if per_token_qs:
                combined_q = per_token_qs[0]
                for pq in per_token_qs[1:]:
                    combined_q &= pq

                # if we had a strict DB match earlier, ensure combined_q respects it
                if db_strict_q is not None:
                    combined_q &= db_strict_q

                if status_value is not None:
                    combined_q &= Q(user__is_active=status_value)

                q = combined_q
        else:
            # single-token search
            if status_value is not None:
                # if the search is just 'active' or 'inactive', filter by status only
                qs = qs.filter(user__is_active=status_value)
                applied_status_only = True
            else:
                q = base_q
                if db_strict_q is not None:
                    q = q & db_strict_q

        if not applied_status_only:
            qs = qs.filter(q).distinct()

    # Sorting Logic
    sort_field = request.GET.get('sort[0][field]')
    sort_dir = request.GET.get('sort[0][dir]')

    if sort_field and sort_dir:
        sort_mapping = {
            'username': 'user__username',
            'full_name': ['user__first_name', 'user__last_name'],
            'role': 'user__userauth__user_permission__name',
            'group': 'team__user_group__group_name',
            'team': 'team__name',
            'phone': 'phone',
            'status': 'user__is_active',
            'create_by': 'user__userauth',
        }
        
        if sort_field in sort_mapping:
            fields = sort_mapping[sort_field]
            if not isinstance(fields, list):
                fields = [fields]
            
            ordering = []
            for f in fields:
                ordering.append(f'-{f}' if sort_dir == 'desc' else f)
            qs = qs.order_by(*ordering)
            if sort_field == 'role':
                qs = qs.distinct()
    else:
        qs = qs.order_by('user__username')

    # annotate profile instances with permission and database_servers for use in serialization
    for profile in qs:
        auths = auth_map.get(profile.user_id, [])
        profile.permission = auths[0].user_permission.name if auths else None
        allowed_db_ids = {auth.maindatabase_id for auth in auths}
        if allowed_db_ids:
            profile.database_servers = [auth.maindatabase.database_name for auth in auths]
        else:
            profile.database_servers = None

    # paging parameters (DataTables style)
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 25))
    try:
        start = max(0, int(start))
    except Exception:
        start = 0
    try:
        length = max(1, min(1000, int(length)))
    except Exception:
        length = 25

    records_total = qs.count()
    page_qs = qs[start:start + length]

    serializer = UserProfileSerializer(page_qs, many=True).data
    # inject computed fields (permission, database_servers) into serialized data
    data = list(serializer)
    for i, profile in enumerate(page_qs):
        try:
            data[i]['permission'] = getattr(profile, 'permission', None)
            data[i]['database_servers'] = getattr(profile, 'database_servers', None)
            # include creator info if available
            try:
                cb = getattr(profile, 'create_by', None)
                if cb:
                    try:
                        fname = getattr(cb, 'first_name', '') or ''
                        lname = getattr(cb, 'last_name', '') or ''
                        full = (fname + ' ' + lname).strip()
                        data[i]['create_by'] = full if full else getattr(cb, 'username', None)
                    except Exception:
                        data[i]['create_by'] = getattr(cb, 'username', None)
                else:
                    data[i]['create_by'] = None
            except Exception:
                data[i]['create_by'] = None
            # format create_at to 'YYYY-MM-DD HH:MM:SS'
            try:
                ca = data[i].get('create_at')
                if ca:
                    if isinstance(ca, str):
                        cs = ca
                        if cs.endswith('Z'):
                            cs = cs[:-1] + '+00:00'
                        try:
                            dt = datetime.fromisoformat(cs)
                        except Exception:
                            # fallback: try parsing without microseconds
                            try:
                                dt = datetime.strptime(cs.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                            except Exception:
                                dt = None
                    elif isinstance(ca, (int, float)):
                        dt = datetime.fromtimestamp(ca)
                    else:
                        dt = ca

                    if dt and hasattr(dt, 'strftime'):
                        data[i]['create_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
        except Exception:
            pass
        

    # If we previously detected matching_db_ids for the original search_term,
    # as a final safeguard only include serialized rows that actually list
    # that database in their `database_servers` array.
    try:
        if search_term and 'matching_db_ids' in locals() and matching_db_ids:
            def _norm(s):
                return re.sub(r'[^0-9A-Za-z]+', '', (s or '')).lower()

            norm_search = _norm(search_term)
            if norm_search:
                filtered = []
                for row in data:
                    dbs = row.get('database_servers') or []
                    for dbn in dbs:
                        if norm_search in _norm(dbn):
                            filtered.append(row)
                            break
                data = filtered
    except Exception:
        pass

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': len(data),
        'data': data
    })

@login_required
@require_action('Change Status')
@require_POST
def ApiChangeUserStatus(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        if user == request.user:
            return JsonResponse({'status': 'error', 'message': 'Cannot change your own status.'})
        user.is_active = not user.is_active
        user.save()
        status_msg = 'Active' if user.is_active else 'Inactive'
        create_user_log(user=request.user, action="Change User Status", detail=f"Changed status of {user.username} to {status_msg}", status="success", request=request)
        return JsonResponse({'status': 'success', 'message': f'User {user.username} is now {status_msg}.'})
    except User.DoesNotExist:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : User not found", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': 'User not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : {str(e)}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/login')
@require_action('Role & Permissions')
def ApiGetAllRolesPermissions(request):
    try:
        admin_role = UserPermission.objects.filter(type='administrator').first()
        all_perms_data = []
        
        if admin_role:
            details = UserPermissionDetail.objects.filter(user_permission=admin_role).order_by('id')
            for d in details:
                all_perms_data.append({
                    'action': d.action,
                    'name': d.action.replace('-', ' ').title(), 
                    'type': d.type
                })

        roles = UserPermission.objects.all()
        roles_permissions = {}
        custom_roles = []

        for role in roles:
            active_actions = list(UserPermissionDetail.objects.filter(
                user_permission=role, 
                status=True
            ).values_list('action'))
            
            if role.type in ['administrator', 'auditor', 'operator']:
                roles_permissions[role.type] = {
                    'id': role.id,
                    'permissions': active_actions
                }
            else:
                custom_roles.append({
                    'id': role.id,
                    'name': role.name,
                    'permissions': active_actions
                })

        return JsonResponse({
            'status': 'success',
            'all_permissions': all_perms_data,
            'base_roles': roles_permissions,
            'custom_roles': custom_roles
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/login')
def ApiGetUSerProfile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        # if user == request.user:
        #     return JsonResponse({'status': 'error', 'message': 'Cannot access your own profile here.'})

        user_to_edit = user
        user_profile = UserProfile.objects.filter(user=user_to_edit).first()

        user_auths = UserAuth.objects.filter(user=user_to_edit)
        selected_db_ids = [str(auth.maindatabase.id) for auth in user_auths if getattr(auth, 'allow', False)]
        
        main_db_qs = MainDatabase.objects.all()
        main_db = [
            {
                'id': d.id,
                'database_name': getattr(d, 'database_name', None),
                'status': getattr(d, 'status', None)
            }
            for d in main_db_qs
        ]

        all_db_selected = len(selected_db_ids) == len(main_db) and len(main_db) > 0

        user_permission = None
        if user_auths.exists() and user_auths.first().user_permission:
            user_permission = user_auths.first().user_permission

        selected_role_id = None
        selected_role_type = None
        if user_permission:
            if user_permission.type in ['administrator', 'auditor', 'operator']:
                selected_role_type = user_permission.type
            else:
                selected_role_id = str(user_permission.id)

        profile_data = UserProfileSerializer(user_profile).data if user_profile else None

        return JsonResponse({
            'status': 'success',
            'user_profile': profile_data,
            'selected_db_id': selected_db_ids,
            'all_db_selected': all_db_selected,
            'selected_role_id': selected_role_id,
            'selected_role_type': selected_role_type,
            'selected_db_name': profile_data['team']['maindatabase']['database_name'] if profile_data and profile_data.get('team') and profile_data['team'].get('database') else None
        })
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found.'})

@login_required
@require_action('Change Status')
@require_POST
def ChangeUserStatus(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user == request.user:
            return JsonResponse({'status': 'error', 'message': 'Cannot change your own status.'})
            
        user.is_active = not user.is_active
        user.save()
        
        status_msg = "Active" if user.is_active else "Inactive"
        create_user_log(user=request.user, action="Change User Status", detail=f"Changed status of {user.username} to {status_msg}", status="success", request=request)
        
        return JsonResponse({'status': 'success', 'message': f'User is now {status_msg}.'})
    except User.DoesNotExist:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : User not found", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': 'User not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : {str(e)}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})
    
@login_required
@require_action('Delete User')
@require_POST
def ApiDeleteUser(request, user_id):
    """
    Hard deletes a user and cleans up related data to avoid foreign key constraints.
    """
    print('user_id',user_id)
    try:
        user_to_delete = User.objects.get(id=user_id)

        if user_to_delete.is_superuser:
            create_user_log(user=request.user, action="Delete User", detail=f"Attempted to delete superuser: {user_to_delete.username}", status="error", request=request)
            return JsonResponse({'status': 'error', 'message': 'Cannot delete a superuser.'})
        if user_to_delete == request.user:
            create_user_log(user=request.user, action="Delete User", detail=f"Attempted to delete self: {user_to_delete.username}", status="error", request=request)
            return JsonResponse({'status': 'error', 'message': 'Cannot delete your own account.'})

        username = user_to_delete.username 
        
        with transaction.atomic():
            # 1. ลบ Logs ของ User นี้ก่อน (มักเป็นสาเหตุหลักของ FK Constraint แบบ PROTECT)
            # UserLog.objects.filter(user=user_to_delete).delete()
            
            # 2. ลบข้อมูล Auth และ Profile (ปกติจะเป็น CASCADE แต่ลบเพื่อความชัวร์)
            UserAuth.objects.filter(user=user_to_delete).delete()
            UserProfile.objects.filter(user=user_to_delete).delete()
            
            # 3. ลบ User ออกจากระบบ
            user_to_delete.delete()

        create_user_log(user=request.user, action="Delete User", detail=f"Successfully deleted user: {username} (ID: {user_id})", status="success", request=request)
        return JsonResponse({'status': 'success', 'message': 'User deleted successfully.', 'username': username})
    except User.DoesNotExist:
        create_user_log(user=request.user, action="Delete User", detail=f"Attempted to delete non-existent user with ID: {user_id}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': 'User not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Delete User", detail=f"Failed to delete user with ID: {user_id}", status="error", request=request, exception=e)
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})

@login_required(login_url='/login')
def ApiCheckUsername(request):
    username = request.GET.get('username', None)
    user_id = request.GET.get('user_id', None)
    if not username:
        return JsonResponse({'status': 'error', 'message': 'Username is required'})
    
    query = User.objects.filter(username=username)
    if user_id:
        query = query.exclude(id=user_id)

    if query.exists():
        return JsonResponse({'status': 'success', 'is_taken': True, 'message': 'This name is already in the system.'})
    else:
        return JsonResponse({'status': 'success', 'is_taken': False})

@login_required(login_url='/login')
@require_action('Add User', 'Edit User')
@require_POST
def ApiSaveUser(request, user_id=None):
    """สร้างหรืออัพเดตผู้ใช้

    ถ้าใน POST มีค่าของ `user_id` ให้ทำการอัพเดต มิฉะนั้นให้สร้างผู้ใช้ใหม่
    """
    User = get_user_model()
    post_data = request.POST.dict()

    # ฟิลด์ทั่วไป
    # ให้ยก user_id ที่มาจาก path parameter (ถ้ามี) ไว้ก่อน
    post_user_id = post_data.get('user_id')
    # ถ้า user_id ถูกส่งจาก URL (path) ให้ใช้ค่านั้นก่อน หากไม่มีก็ใช้ค่าใน POST
    user_id = user_id or post_user_id
    username = post_data.get('username')
    password = post_data.get('password')
    email = post_data.get('email')
    first_name = post_data.get('first_name')
    last_name = post_data.get('last_name')
    phone = post_data.get('phone')

    # บทบาทและทีม
    role_input = post_data.get('role')
    team_id = post_data.get('team')

    user_permission_obj = None
    if role_input:
        if str(role_input).isdigit():
            user_permission_obj = UserPermission.objects.filter(id=role_input).first()
        else:
            user_permission_obj = UserPermission.objects.filter(type=role_input).first()

    team_obj = UserTeam.objects.filter(id=team_id).first() if team_id else None

    # ตรวจสิทธิ์: ถ้าเป็นอัพเดต ต้องมี 'Edit User' ถ้าสร้างต้องมี 'Add User'
    user_actions = get_user_actions(request.user)
    if user_id:
        if 'Edit User' not in user_actions:
            return JsonResponse({'status': 'error', 'message': 'Access Denied'}, status=403)
    else:
        if 'Add User' not in user_actions:
            return JsonResponse({'status': 'error', 'message': 'Access Denied'}, status=403)

    # กรณีอัพเดตเมื่อมี user_id
    if user_id:
        try:
            user_to_update = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found.'})

        # ตรวจสอบความซ้ำของ username โดยยกเว้นตัวเอง
        new_username = username or user_to_update.username
        if User.objects.filter(username=new_username).exclude(id=user_id).exists():
            return JsonResponse({"status": "error", "message": "This name is already in the system."})

        try:
            with transaction.atomic():
                user_to_update.username = new_username
                user_to_update.first_name = first_name or user_to_update.first_name
                user_to_update.last_name = last_name or user_to_update.last_name
                user_to_update.email = email or user_to_update.email

                if password:
                    user_to_update.set_password(password)
                user_to_update.save()

                # อัพเดตโปรไฟล์
                profile_to_update = UserProfile.objects.filter(user=user_to_update).first()
                if profile_to_update:
                    profile_to_update.phone = phone or profile_to_update.phone
                    if team_id:
                        profile_to_update.team = UserTeam.objects.filter(id=team_id).first()
                    profile_to_update.save()
                else:
                    # create profile if missing
                    UserProfile.objects.create(user=user_to_update, phone=phone, team=team_obj)

                # รีเซ็ต UserAuth (ลบของเก่าแล้วสร้างใหม่)
                UserAuth.objects.filter(user=user_to_update).delete()

                main_dbs = MainDatabase.objects.all()
                is_all_dbs = post_data.get('db_id-all') == 'all'

                user_auths = []
                for db in main_dbs:
                    allow = True if is_all_dbs else bool(post_data.get(f'db_id-{db.id}', None))
                    user_auths.append(UserAuth(
                        user=user_to_update,
                        maindatabase=db,
                        allow=allow,
                        user_permission=user_permission_obj
                    ))
                UserAuth.objects.bulk_create(user_auths)

            create_user_log(user=request.user, action="Update User", detail=f"Updated user: {user_to_update.username}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'User updated successfully.', 'username': user_to_update.username})

        except IntegrityError as e:
            error_message = str(e)
            create_user_log(user=request.user, action="Update User", detail=f"IntegrityError: {error_message}", status="error", request=request)
            return JsonResponse({"status": "error", "message": "Error: " + error_message})
        except Exception as e:
            create_user_log(user=request.user, action="Update User", detail=f"Error updating user: {str(e)}", status="error", request=request)
            return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})

    # กรณีสร้างผู้ใช้
    # ตรวจสอบว่าชื่อผู้ใช้มีอยู่แล้วหรือไม่
    if not username:
        return JsonResponse({'status': 'error', 'message': 'Username is required'})

    if User.objects.filter(username=username).exists():
        return JsonResponse({"status": "error", "message": "This name is already in the system."})

    try:
        with transaction.atomic():
            auth_user_create = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=True,
            )

            if auth_user_create:
                main_dbs = list(MainDatabase.objects.only('id').order_by('id'))

                is_all_dbs = post_data.get('db_id-all') == 'all'

                user_auths = []
                for db in main_dbs:
                    if is_all_dbs:
                        db_select = post_data.get(f'db_id-{db.id}', None)
                        allow = True
                    else:
                        db_select = post_data.get(f'db_id-{db.id}', None)
                        allow = bool(db_select)
                    user_auths.append(UserAuth(
                        user=auth_user_create,
                        maindatabase=db,
                        allow=allow,
                        user_permission=user_permission_obj
                    ))
                UserAuth.objects.bulk_create(user_auths)

                UserProfile.objects.create(
                    user=auth_user_create,
                    phone=phone,
                    team=team_obj,
                    create_by=request.user
                )

            context = {
                'status': "success",
                'message': "User created successfully",
                'username': username
            }
            create_user_log(user=request.user, action="Created User", detail=f"User created successfully: {username}", status="success", request=request)
        return JsonResponse(context)

    except IntegrityError as e:
        error_message = str(e)
        create_user_log(user=request.user, action="Created User",  detail=f"IntegrityError: {error_message}", status="error", request=request)
        return JsonResponse({"status": "error", "message": "Error: " + error_message})

    except Exception as e:
        create_user_log(user=request.user, action="Created User", detail=f"Error: {str(e)}", status="error", request=request)
        return JsonResponse({"status": "error", "message": f"Error: {str(e)}"})

@login_required
@require_action('Reset password')
@require_POST
def ApiResetPassword(request, user_id):
    """
    Resets a user's password.
    """
    try:
        user = User.objects.get(id=user_id)
        user.set_password(user.username)
        user.save()
        
        create_user_log(user=request.user, action="Reset Password", detail=f"Successfully reset password for user: {user.username} (ID: {user_id})", status="success", request=request)
        return JsonResponse({'status': 'success', 'message': f'Password reset successful.'+'<br>'+ f'Password is: <b>{user.username}</b> (username)' })
    except User.DoesNotExist:
        create_user_log(user=request.user, action="Reset Password", detail=f"Attempted to reset password for non-existent user with ID: {user_id}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': 'User not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Reset Password", detail=f"Failed to reset password for user with ID: {user_id}", status="error", request=request, exception=e)
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})

@login_required(login_url='/login')
@require_POST
def ApiChangePassword(request):
    user = request.user
    old_password = request.POST.get('old_password')
    new_password = request.POST.get('new_password')

    # frontend may send JSON (application/json). Parse JSON body if present.
    try:
        content_type = request.META.get('CONTENT_TYPE', '') or request.content_type or ''
    except Exception:
        content_type = ''

    if ('application/json' in content_type) and not (old_password and new_password):
        try:
            body = json.loads(request.body.decode('utf-8') or '{}') if request.body else {}
            old_password = body.get('old_password') or old_password
            new_password = body.get('new_password') or new_password
        except Exception:
            pass

    if not user.check_password(old_password):
        return JsonResponse({'status': 'error', 'message': 'Old password is incorrect.'})

    try:
        user.set_password(new_password)
        user.save()
        create_user_log(user=request.user, action="Change Password", detail=f"Successfully changed password for user: {user.username}", status="success", request=request)
        return JsonResponse({'status': 'success', 'message': 'Password changed successfully.'})
    except Exception as e:
        create_user_log(user=request.user, action="Change Password", detail=f"Failed to change password for user: {user.username}", status="error", request=request, exception=e)
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})