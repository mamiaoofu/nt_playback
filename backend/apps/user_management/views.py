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

    # apply search filter if provided (DataTables style: search[value])
    search_term = (request.GET.get('search[value]') or request.GET.get('search') or '').strip()
    if search_term:
        # split on whitespace and common separators (hyphen, slash, underscore)
        tokens = [t for t in re.split(r'[\s\-_/]+', search_term) if t]
        base_q = (
            Q(user__username__icontains=search_term)
            | Q(user__first_name__icontains=search_term)
            | Q(user__last_name__icontains=search_term)
            | Q(phone__icontains=search_term)
            | Q(team__name__icontains=search_term)
            | Q(user_code__icontains=search_term)
            | Q(user__userauth__maindatabase__database_name__icontains=search_term)
            | Q(user__userauth__user_permission__name__icontains=search_term)
        )

        # detect explicit or partial status tokens (allow partial like 'inac' or 'act')
        status_value = None
        exact_status = {t.lower() for t in tokens if t.lower() in ('active', 'inactive')}
        if 'active' in exact_status and 'inactive' not in exact_status:
            status_value = True
        elif 'inactive' in exact_status and 'active' not in exact_status:
            status_value = False
        else:
            # allow partial/ prefix matches for status tokens (accept shorter prefixes)
            partial_hits = set()
            for t in tokens:
                lt = t.lower()
                # consider prefixes of length >= 2 to be helpful for users (e.g., 'ac' or 'inc')
                if len(lt) >= 2:
                    added = False
                    # prefer prefix matches to avoid accidental substring collisions
                    if 'active'.startswith(lt) and not 'inactive'.startswith(lt):
                        partial_hits.add('active')
                        added = True
                    if 'inactive'.startswith(lt) and not 'active'.startswith(lt):
                        partial_hits.add('inactive')
                        added = True
                    if not added:
                        # fallback to substring matching when prefix rules are ambiguous
                        hit = []
                        if 'active'.find(lt) != -1:
                            hit.append('active')
                        if 'inactive'.find(lt) != -1:
                            hit.append('inactive')
                        if len(hit) == 1:
                            partial_hits.add(hit[0])
            if 'active' in partial_hits and 'inactive' not in partial_hits:
                status_value = True
            elif 'inactive' in partial_hits and 'active' not in partial_hits:
                status_value = False

        applied_status_only = False

        # build tokenized name/group queries for multi-token searches
        if len(tokens) > 1:
            q_tokens = Q()
            for t in tokens:
                q_tokens &= (
                    Q(user__first_name__icontains=t) | Q(user__last_name__icontains=t)
                )
            # also try matching all tokens across group/team fields (e.g. "Group - Team")
            q_tokens_group = Q()
            for t in tokens:
                q_tokens_group &= (
                    Q(team__name__icontains=t) | Q(team__user_group__group_name__icontains=t)
                )

            # if a status token exists alongside other tokens, require status AND the other tokens
            if status_value is not None:
                q = (base_q | q_tokens | q_tokens_group) & Q(user__is_active=status_value)
            else:
                q = base_q | q_tokens | q_tokens_group
        else:
            # single-token search
            if status_value is not None:
                # if the search is just 'active' or 'inactive', filter by status only
                qs = qs.filter(user__is_active=status_value)
                applied_status_only = True
            else:
                q = base_q

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
            'status': 'user__is_active'
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
        qs = qs.order_by('-user__date_joined')

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
        except Exception:
            pass
        

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_total,
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
                    team=team_obj
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