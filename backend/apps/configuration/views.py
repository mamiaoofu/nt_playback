# apps/home/views.py
from django.shortcuts import render, redirect
from functools import wraps
from django.contrib.auth.decorators import login_required
# from apps.page_notfound.views import page_not_found
from apps.core.utils.function import BaseListAPIView, PageNumberPagination
from django.db.models import Q
from django.http import JsonResponse,FileResponse,Http404
from django.core import serializers
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.db import transaction, DatabaseError,IntegrityError
import socket
import uuid
import os
from django.conf import settings
from user_agents import parse
from django.utils import timezone
import json

from apps.core.utils.function import create_user_log, get_user_os_browser_architecture
from apps.core.utils.permissions import  require_action

# models
from apps.core.model.authorize.models import UserAuth,MainDatabase,UserLog,UserGroup,UserTeam
from apps.configuration.models import UserPermission,UserPermissionDetail

#serializer
from apps.core.model.authorize.serializers import MainDatabaseSerializer

class MainDatabaseAPIView(BaseListAPIView):
    serializer_class = MainDatabaseSerializer

    def get_queryset(self):
        queryset = MainDatabase.objects.all()
        return queryset

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
@require_action('Role & Permissions')
def ApiIndexRole(request):
    
    base_user_permission_qs = UserPermission.objects.filter(type__in=["administrator", "auditor", "operator"])
    user_permission_other_qs = UserPermission.objects.exclude(type__in=["administrator", "auditor", "operator"])
    user_permission_detail_qs = UserPermissionDetail.objects.exclude(user_permission__in=["1", "2", "3"])

    # Convert QuerySets to plain lists/dicts so JsonResponse can serialize them
    base_user_permission = list(base_user_permission_qs.values())
    user_permission_other = list(user_permission_other_qs.values())
    user_permission_detail = list(user_permission_detail_qs.values())

    return JsonResponse({
        'base_user_permission': base_user_permission,
        'user_permission_other': user_permission_other,
        'user_permission_detail': user_permission_detail,
    })

@login_required(login_url='/login')
@require_action('Role & Permissions')
def ApiGetRoleDetails(request, role_id):
    try:
        role_id = int(role_id)
    except (ValueError, TypeError):
        return JsonResponse({'status': False, 'message': 'Invalid role_id'}, status=400)

    role = UserPermission.objects.filter(pk=role_id).first()
    if not role:
        return JsonResponse({'status': False, 'message': 'Role not found'}, status=404)

    # Basic permission check: only staff or users with explicit permission may view role details
    # user = request.user
    # if not (user.is_staff or user.has_perm('configuration.view_userpermission')):
    #     return JsonResponse({'status': False, 'message': 'Permission denied'}, status=403)

    details = UserPermissionDetail.objects.filter(user_permission=role).order_by('action', 'id')

    all_permissions = []
    role_permissions = []
    default_permissions = []

    for detail in details:
        all_permissions.append({
            'action': detail.action,
            'name': f"{detail.action}",
            'type': detail.type,
            'id': detail.id
        })

        if detail.status:
            role_permissions.append(detail.action)

        if detail.default:
            default_permissions.append(detail.action)

    return JsonResponse({
        'status': True,
        'role_name': role.name,
        'role_type': role.type,
        'all_permissions': all_permissions,
        'role_permissions': role_permissions,
        'default_permissions': default_permissions
    })
    
@login_required(login_url='/login')
@require_action('Group & Team')    
def ApiIndexGroup(request):
    user_group = UserGroup.objects.filter(status=1).order_by('group_name')
    user_team = UserTeam.objects.filter(status=1).order_by('name')
    database = MainDatabase.objects.filter(status=1)
    
    return JsonResponse({
        'user_group': list(user_group.values()),
        'user_team': list(user_team.values()),
        'database': list(database.values()),
    })

@login_required(login_url='/login')
@require_action('Group & Team')    
def ApiGetTeamByGroup(request, group_id):
    try:
        group_id = int(group_id)
    except (ValueError, TypeError):
        return JsonResponse({'status': False, 'message': 'Invalid group_id'}, status=400)
    
    teams = UserTeam.objects.filter(user_group_id=group_id, status=1).select_related('user_group').order_by('name')
    
    team_list = []
    for team in teams:
        team_list.append({
            'id': team.id,
            'name': team.name,
            'group_name': team.user_group.group_name
        })
        
    return JsonResponse({'status': 'success', 'teams': team_list})

@login_required(login_url='/login')
@require_action('Role & Permissions')   
def ApiCheckRoleName(request):
    role_name = request.GET.get('role_name', None)
    role_id = request.GET.get('role_id', None)
    if not role_name:
        return JsonResponse({'status': 'error', 'message': 'Role name is required'})
    
    query = UserPermission.objects.filter(name=role_name)
    if role_id:
        query = query.exclude(id=role_id)

    if query.exists():
        return JsonResponse({'status': 'success', 'is_taken': True, 'message': 'This name is already in the system.'})
    else:
        return JsonResponse({'status': 'success', 'is_taken': False})

@require_POST
@login_required(login_url='/login')
@require_action('Role & Permissions')   
def ApiSaveRole(request, role_id=None):
    """
    Create a new role or update an existing one.
    If POST JSON contains `role_id`, perform update; otherwise create a new role.
    """
    try:
        data = json.loads(request.body)
        # prefer role_id from URL if provided, otherwise check POST body
        if role_id is None:
            role_id = data.get('role_id')
        else:
            # ensure we have a consistent type (int)
            try:
                role_id = int(role_id)
            except Exception:
                pass

        # role_name may be optional for update flows; only require it for create
        role_name_raw = data.get('role_name', None)
        role_name = role_name_raw.strip() if isinstance(role_name_raw, str) else None
        permissions = data.get('permissions', [])  # List of action IDs

        # If no role_id provided, this is a create flow and role_name is required.
        if not role_id and not role_name:
            return JsonResponse({'status': 'error', 'message': 'Role name is required.'})

        # Update flow
        if role_id:
            role = UserPermission.objects.filter(id=role_id).first()
            if not role:
                return JsonResponse({'status': 'error', 'message': 'Role not found.'})

            # If a new role_name was provided, check duplicates (excluding current role)
            if role_name:
                if UserPermission.objects.filter(name__iexact=role_name).exclude(id=role_id).exists():
                    return JsonResponse({'status': 'error', 'message': 'Role name already exists.'})

            with transaction.atomic():
                # Only update the role name when provided (allow permission-only updates)
                if role_name:
                    role.name = role_name
                    role.save()

                # Update Permissions
                details = UserPermissionDetail.objects.filter(user_permission=role)
                for detail in details:
                    is_active = str(detail.action) in map(str, permissions)
                    detail.status = is_active
                    detail.save()

                create_user_log(user=request.user, action="Update Custom Role", detail=f"Updated role: {role_name}", status="success", request=request)

            return JsonResponse({'status': 'success', 'message': 'Role updated successfully.', 'role': {'id': role.id, 'name': role.name}})

        # Create flow
        # Check for duplicate name
        if UserPermission.objects.filter(name__iexact=role_name).exists():
            return JsonResponse({'status': 'error', 'message': 'Role name already exists.'})

        with transaction.atomic():
            # Create Role
            new_role = UserPermission.objects.create(type='role_other', name=role_name)

            # Use 'administrator' as a template for all possible actions
            admin_role = UserPermission.objects.filter(type='administrator').first()

            if admin_role:
                admin_details = UserPermissionDetail.objects.filter(user_permission=admin_role)
                new_details = []

                for detail in admin_details:
                    # Check if this action is in the selected permissions
                    is_active = str(detail.action) in map(str, permissions)

                    new_details.append(UserPermissionDetail(
                        user_permission=new_role,
                        action=detail.action,
                        status=is_active,
                        type=detail.type,
                        default='t' if is_active else 'f'
                    ))

                UserPermissionDetail.objects.bulk_create(new_details)

            # Log the action
            create_user_log(user=request.user, action="Create Custom Role", detail=f"Created role: {role_name}", status="success", request=request)

        return JsonResponse({
            'status': 'success',
            'message': 'Role created successfully.',
            'role': {
                'id': new_role.id,
                'name': new_role.name,
                'type': new_role.type
            }
        })

    except Exception as e:
        create_user_log(user=request.user, action="Create/Update Custom Role", detail=f"Error creating/updating role: {str(e)}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
@login_required(login_url='/login')
@require_action('Role & Permissions', 'Delete Custom Role')  
def ApiDeleteRole(request, role_id=None):
    try:
        body_role_id = None
        try:
            data = json.loads(request.body) if request.body else {}
            body_role_id = data.get('role_id')
        except Exception:
            body_role_id = None

        # prefer role_id from URL if provided, otherwise fall back to body
        rid = role_id or body_role_id
        if not rid:
            return JsonResponse({'status': 'error', 'message': 'No role id provided.'})

        role = UserPermission.objects.filter(id=rid).first()
        if role:
            # capture values before deletion
            deleted_id = role.id
            deleted_name = role.name
            role.delete()
            create_user_log(user=request.user, action="Delete Custom Role", detail=f"Deleted role: {deleted_name}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Role deleted successfully.', 'role': {'id': deleted_id, 'name': deleted_name}})

        return JsonResponse({'status': 'error', 'message': 'Role not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Delete Custom Role", detail=f"Error deleting role: {str(e)}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_GET
@login_required(login_url='/login')
@require_action('Group & Team')   
def ApiCheckGroupName(request):
    group_name = request.GET.get('group_name', None)
    group_id = request.GET.get('group_id', None)
    if not group_name:
        return JsonResponse({'status': 'error', 'message': 'Group name is required'})
    
    query = UserGroup.objects.filter(group_name=group_name)
    if group_id:
        query = query.exclude(id=group_id)

    if query.exists():
        return JsonResponse({'status': 'success', 'is_taken': True, 'message': 'This group name is already in the system.'})
    else:
        return JsonResponse({'status': 'success', 'is_taken': False})
    
@require_GET
@login_required(login_url='/login')
@require_action('Group & Team')   
def ApiCheckTeamName(request):
    team_name = request.GET.get('team_name', None)
    team_id = request.GET.get('team_id', None)
    group_id = request.GET.get('group_id', None)
    if not team_name:
        return JsonResponse({'status': 'error', 'message': 'Team name is required'})
    
    # Scope uniqueness check to a specific group when `group_id` is provided.
    # Use case-insensitive comparison like other name checks.
    query = UserTeam.objects.filter(name__iexact=team_name)
    if group_id:
        try:
            gid = int(group_id)
            query = query.filter(user_group_id=gid)
        except (ValueError, TypeError):
            # ignore invalid group_id and fall back to global check
            pass

    if team_id:
        try:
            tid = int(team_id)
            query = query.exclude(id=tid)
        except (ValueError, TypeError):
            pass

    if query.exists():
        return JsonResponse({'status': 'success', 'is_taken': True, 'message': 'This team name is already in the system.'})
    else:
        return JsonResponse({'status': 'success', 'is_taken': False})
    
@require_POST
@login_required(login_url='/login')
@require_action('Group & Team')   
def ApiSaveGroup(request):
    """
    Single endpoint to Create / Update / Delete a UserGroup.
    JSON body should include `action` = 'create'|'update'|'delete'.
    - create: requires `group_name`, optional `description`.
    - update: requires `group_id`, `group_name`, optional `description`.
    - delete: requires `group_id`.
    Supports form POST as fallback for non-JSON requests.
    """
    try:
        data = {}
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body) if request.body else {}
            except Exception:
                data = {}
        else:
            data = request.POST.dict()

        action = (data.get('action') or '').lower()
        if action not in ('create', 'update', 'delete'):
            return JsonResponse({'status': 'error', 'message': 'Invalid action. Use create, update, or delete.'}, status=400)

        # CREATE
        if action == 'create':
            group_name = (data.get('group_name') or '').strip()
            description = data.get('description', '')

            if not group_name:
                return JsonResponse({'status': 'error', 'message': 'Group name is required.'})

            existing_group = UserGroup.objects.filter(group_name__iexact=group_name).first()
            if existing_group:
                create_user_log(user=request.user, action='Create Config Group', detail=f'Duplicate group : {group_name}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'This group name is already in the system.'})

            try:
                with transaction.atomic():
                    new_group = UserGroup.objects.create(group_name=group_name, description=description, status=1)
                    create_user_log(user=request.user, action='Create Config Group', detail=f'Created group : {group_name} | Description: {description}', status='success', request=request)

                return JsonResponse({'status': 'success', 'group': {'id': new_group.id, 'group_name': new_group.group_name, 'description': new_group.description}})
            except IntegrityError as e:
                create_user_log(user=request.user, action='Create Config Group', detail=f'Database error : {str(e)}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'เกิดข้อผิดพลาดกับฐานข้อมูล'})

        # UPDATE
        if action == 'update':
            group_id = data.get('group_id')
            group_name = (data.get('group_name') or '').strip()
            description = data.get('description', '')

            if not group_id or not group_name:
                return JsonResponse({'status': 'error', 'message': 'Group ID and Name are required.'})

            group = UserGroup.objects.filter(id=group_id).first()
            if not group:
                return JsonResponse({'status': 'error', 'message': 'Group not found.'})

            if UserGroup.objects.filter(group_name__iexact=group_name).exclude(id=group_id).exists():
                create_user_log(user=request.user, action='Update Config Group', detail=f'Duplicate group : {group_name}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'This group name is already in the system.'})

            try:
                with transaction.atomic():
                    group.group_name = group_name
                    group.description = description
                    group.save()
                    create_user_log(user=request.user, action='Update Config Group', detail=f'Updated group : {group_name}', status='success', request=request)

                return JsonResponse({'status': 'success', 'group': {'id': group.id, 'group_name': group.group_name, 'description': group.description}})
            except Exception as e:
                create_user_log(user=request.user, action='Update Config Group', detail=f'Error: {str(e)}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': str(e)})

        # DELETE
        if action == 'delete':
            group_id = data.get('group_id')
            if not group_id:
                return JsonResponse({'status': 'error', 'message': 'Group ID is required.'})

            group = UserGroup.objects.filter(id=group_id).first()
            if group:
                group_name = group.group_name
                group.delete()
                create_user_log(user=request.user, action='Delete Config Group', detail=f'Deleted group: {group_name}', status='success', request=request)
                return JsonResponse({'status': 'success', 'message': 'Group deleted successfully.'})

            return JsonResponse({'status': 'error', 'message': 'Group not found.'})

    except IntegrityError as e:
        create_user_log(user=request.user, action='ApiSaveำGroup', detail=f'Database error : {str(e)}', status='error', request=request)
        return JsonResponse({'status': 'error', 'message': 'An error occurred with the database.'})
    except Exception as e:
        create_user_log(user=request.user, action='ApiSaveGroup', detail=f'Unexpected error: {str(e)}', status='error', request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})
    
@require_POST
@login_required(login_url='/login')
@require_action('Group & Team')   
def ApiSaveTeam(request):
    """
    Single endpoint to Create / Update / Delete a UserTeam.
     JSON body should include `action` = 'create'|'update'|'delete'.
    - create: requires `user_group_id => ex. [33177]`, `name` `maindatabase => ex. ["2","3"]`.
    - update: requires `team_id`, `user_group_id => ex. [33177]`, `name` `maindatabase => ex. ["2","3"]`.
    - delete: requires `team_id`.
    Supports form POST as fallback for non-JSON requests.
    """
    try:
        data = {}
        if request.content_type and 'application/json' in request.content_type:
            try:
                data = json.loads(request.body) if request.body else {}
            except Exception:
                data = {}
        else:
            data = request.POST.dict()

        action = (data.get('action') or '').lower()
        if action not in ('create', 'update', 'delete'):
            return JsonResponse({'status': 'error', 'message': 'Invalid action. Use create, update, or delete.'}, status=400)

        # CREATE
        if action == 'create':
            name = (data.get('name') or '').strip()
            user_group_id_raw = data.get('user_group_id')
            maindatabase_raw = data.get('maindatabase')

            if not name:
                return JsonResponse({'status': 'error', 'message': 'Team name is required.'})
            
            # Handle user_group_id (can be list or single value)
            user_group_id = None
            if isinstance(user_group_id_raw, list) and len(user_group_id_raw) > 0:
                user_group_id = user_group_id_raw[0]
            else:
                user_group_id = user_group_id_raw
            
            if not user_group_id:
                return JsonResponse({'status': 'error', 'message': 'User Group is required.'})

            # Handle maindatabase (convert list to JSON string if needed)
            maindatabase_str = '[]'
            if maindatabase_raw:
                if isinstance(maindatabase_raw, list):
                    maindatabase_str = json.dumps(maindatabase_raw)
                else:
                    maindatabase_str = str(maindatabase_raw)

            # Duplicate check: only within the same group (case-insensitive)
            try:
                gid_check = int(user_group_id)
            except Exception:
                gid_check = None

            if gid_check is not None:
                dup_qs = UserTeam.objects.filter(name__iexact=name, user_group_id=gid_check)
            else:
                dup_qs = UserTeam.objects.filter(name__iexact=name)

            if dup_qs.exists():
                create_user_log(user=request.user, action='Create Config Team', detail=f'Duplicate team : {name}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'This team name is already in the system.'})

            try:
                with transaction.atomic():
                    group = UserGroup.objects.filter(id=user_group_id).first()
                    if not group:
                        return JsonResponse({'status': 'error', 'message': 'User Group not found.'})

                    new_team = UserTeam.objects.create(
                        name=name,
                        user_group=group,
                        maindatabase=maindatabase_str,
                        status=1
                    )
                    create_user_log(user=request.user, action='Create Config Team', detail=f'Created team : {name}', status='success', request=request)

                return JsonResponse({'status': 'success', 'team': {'id': new_team.id, 'name': new_team.name, 'user_group_id': new_team.user_group_id}})
            except IntegrityError as e:
                create_user_log(user=request.user, action='Create Config Team', detail=f'Database error : {str(e)}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'เกิดข้อผิดพลาดกับฐานข้อมูล'})

        # UPDATE
        if action == 'update':
            team_id = data.get('team_id')
            name = (data.get('name') or '').strip()
            user_group_id_raw = data.get('user_group_id')
            maindatabase_raw = data.get('maindatabase')

            if not team_id or not name:
                return JsonResponse({'status': 'error', 'message': 'Team ID and Name are required.'})

            team = UserTeam.objects.filter(id=team_id).first()
            if not team:
                return JsonResponse({'status': 'error', 'message': 'Team not found.'})

            # Determine the group to check for duplicates: prefer provided user_group_id, otherwise use team's current group
            user_group_id = None
            if isinstance(user_group_id_raw, list) and len(user_group_id_raw) > 0:
                user_group_id = user_group_id_raw[0]
            else:
                user_group_id = user_group_id_raw

            try:
                check_gid = int(user_group_id) if user_group_id else team.user_group_id
            except Exception:
                check_gid = team.user_group_id

            dup_qs = UserTeam.objects.filter(name__iexact=name, user_group_id=check_gid).exclude(id=team_id)
            if dup_qs.exists():
                create_user_log(user=request.user, action='Update Config Team', detail=f'Duplicate team : {name}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': 'This team name is already in the system.'})

            # Handle user_group_id
            user_group_id = None
            if isinstance(user_group_id_raw, list) and len(user_group_id_raw) > 0:
                user_group_id = user_group_id_raw[0]
            else:
                user_group_id = user_group_id_raw

            # Handle maindatabase
            maindatabase_str = team.maindatabase
            if maindatabase_raw is not None:
                if isinstance(maindatabase_raw, list):
                    maindatabase_str = json.dumps(maindatabase_raw)
                else:
                    maindatabase_str = str(maindatabase_raw)

            try:
                with transaction.atomic():
                    if user_group_id:
                        group = UserGroup.objects.filter(id=user_group_id).first()
                        if group:
                            team.user_group = group
                    
                    team.name = name
                    team.maindatabase = maindatabase_str
                    team.save()
                    create_user_log(user=request.user, action='Update Config Team', detail=f'Updated team : {name}', status='success', request=request)

                return JsonResponse({'status': 'success', 'team': {'id': team.id, 'name': team.name}})
            except Exception as e:
                create_user_log(user=request.user, action='Update Config Team', detail=f'Error: {str(e)}', status='error', request=request)
                return JsonResponse({'status': 'error', 'message': str(e)})

        # DELETE
        if action == 'delete':
            team_id = data.get('team_id')
            if not team_id:
                return JsonResponse({'status': 'error', 'message': 'Team ID is required.'})

            team = UserTeam.objects.filter(id=team_id).first()
            if team:
                team_name = team.name
                team.delete()
                create_user_log(user=request.user, action='Delete Config Team', detail=f'Deleted team: {team_name}', status='success', request=request)
                return JsonResponse({'status': 'success', 'message': 'Team deleted successfully.'})

            return JsonResponse({'status': 'error', 'message': 'Team not found.'})

    except IntegrityError as e:
        create_user_log(user=request.user, action='ApiSaveTeam', detail=f'Database error : {str(e)}', status='error', request=request)
        return JsonResponse({'status': 'error', 'message': 'An error occurred with the database.'})
    except Exception as e:
        create_user_log(user=request.user, action='ApiSaveTeam', detail=f'Unexpected error: {str(e)}', status='error', request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})