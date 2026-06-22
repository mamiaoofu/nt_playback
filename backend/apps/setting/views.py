import json
from django.shortcuts import  redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from apps.core.utils.function import create_user_log, get_user_os_browser_architecture
from apps.core.utils.permissions import  require_action
from apps.core.utils.permission_ids import PermissionIDs

from apps.home.models import SetColumnAudioRecord

@login_required
@require_GET
@require_action(PermissionIDs.SET_COLUMN, PermissionIDs.AUDIO_RECORDS_ACCESS, PermissionIDs.DELEGATE_FILES)
def ApiGetColumnAudioRecord(request):
    try:
        user = request.user
        is_active = request.GET.get('active')
        
        query = SetColumnAudioRecord.objects.filter(user=user, status=1)
        
        if is_active == 'true':
            query = query.filter(use=True)
            
        set_column = query.all()
        
        return JsonResponse({"data": list(set_column.values('id', 'raw_data','status','name','description', 'use'))}, status=200)
    except Exception as e:
        create_user_log(user=request.user, action="Get Column Audio Record", detail=str(e), status="error", request=request)
        return JsonResponse({"error": "An error occurred while fetching column settings."}, status=500)
        
@login_required
@require_POST
@require_action(PermissionIDs.SET_COLUMN, PermissionIDs.DELEGATE_FILES)
def ApiSaveColumnAudioRecord(request):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        user = request.user

        if action == 'delete':
            record_id = data.get('id')
            try:
                record = SetColumnAudioRecord.objects.get(id=record_id, user=user)
                name = record.name
                record.delete()
                create_user_log(user=user, action="Delete Column Audio Records", detail=f"Column Name : {name}", status="success", request=request)
                return JsonResponse({'status': 'success', 'message': 'Deleted successfully'})
            except SetColumnAudioRecord.DoesNotExist:
                create_user_log(user=user, action="Delete Column Audio Records", detail=f"Record not found for ID: {record_id}", status="error", request=request)
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)

        elif action == 'toggle':
            record_id = data.get('id')
            use_status = data.get('use')
            
            try:
                record = SetColumnAudioRecord.objects.get(id=record_id, user=user)
            except SetColumnAudioRecord.DoesNotExist:
                create_user_log(user=user, action="Toggle Column Audio Record", detail=f"Record not found for ID: {record_id}", status="error", request=request)
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)
            
            if use_status:
                # Enable this one, disable others
                SetColumnAudioRecord.objects.filter(user=user).update(use=False)
                create_user_log(user=user, action="Enable Column Audio Records", detail=f"Column Name : {record.name} to Enable", status="success", request=request)
                record.use = True
            else:
                create_user_log(user=user, action="Disable Column Audio Records", detail=f"Column Name : {record.name} to Disable", status="success", request=request)
                record.use = False
            
            record.save()
            # create_user_log(user=user, action="Toggle Column Audio Record", detail=f"Toggle use status: {record.name} > {record.use}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Status updated successfully'})

        # Common fields for create/update
        name = data.get('name', '').strip()
        description = data.get('description', '')
        raw_data = data.get('raw_data', '')

        if not name:
            create_user_log(user=user, action="Add Column Audio Records", detail="Name is required", status="error", request=request)
            return JsonResponse({'status': 'error', 'message': 'Name is required'}, status=400)

        if action == 'create':
            if SetColumnAudioRecord.objects.filter(user=user, name=name).exists():
                return JsonResponse({'status': 'error', 'message': 'Name already exists'}, status=400)
            
            SetColumnAudioRecord.objects.create(
                user=user,
                name=name,
                description=description,
                raw_data=raw_data,
                status=1
            )
            create_user_log(user=user, action="Add Column Audio Records", detail=f"Column Name : {name}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': f'Created {name} successfully'})

        elif action == 'update':
            record_id = data.get('id')
            try:
                record = SetColumnAudioRecord.objects.get(id=record_id, user=user)
            except SetColumnAudioRecord.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)

            if SetColumnAudioRecord.objects.filter(user=user, name=name).exclude(id=record_id).exists():
                return JsonResponse({'status': 'error', 'message': 'Name already exists'}, status=400)

            record.name = name
            record.description = description
            record.raw_data = raw_data
            record.save()
            
            create_user_log(user=user, action="Edit Column Audio Records", detail=f"Column Name : {name}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': f'Updated {name} successfully'})
        
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        create_user_log(user=request.user, action="Add Column Audio Records", detail=str(e), status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_action(PermissionIDs.SETTING_ACCESS)
def ApiActiveDirectorySetting(request):
    try:
        from apps.setting.models import ActiveDirectorySetting
        config = ActiveDirectorySetting.objects.first()
        if not config:
            config = ActiveDirectorySetting()

        if request.method == 'GET':
            return JsonResponse({
                'status': 'success',
                'data': {
                    'host': config.server_uri,
                    'domain': config.domain,
                    'baseDn': config.base_dn,
                    'username': config.bind_user,
                    'password': '******' if config.bind_password else ''
                }
            })

        elif request.method == 'POST':
            data = json.loads(request.body)
            with transaction.atomic():
                db_config, created = ActiveDirectorySetting.objects.get_or_create(id=1)
                db_config.server_uri = data.get('host', '').strip()
                db_config.domain = data.get('domain', '').strip()
                db_config.base_dn = data.get('baseDn', '').strip()
                db_config.bind_user = data.get('username', '').strip()
                
                password = data.get('password', '')
                if password and password != '******':
                    db_config.set_password(password)
                elif not password:
                    db_config.bind_password = None
                
                db_config.save()
                
            create_user_log(user=request.user, action="Update AD Config", detail="Updated Active Directory settings in DB", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Active Directory settings updated successfully.'})

    except Exception as e:
        create_user_log(user=request.user, action="Update AD Config", detail=str(e), status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_action(PermissionIDs.SETTING_ACCESS)
def ApiNetworkShareSetting(request):
    try:
        from apps.core.model.authorize.models import MainDatabase
        from apps.home.models import FileStorageConfig
        
        if request.method == 'GET':
            databases = MainDatabase.objects.all().order_by('database_name')
            configs = FileStorageConfig.objects.all()
            config_map = {cfg.main_db_id: cfg for cfg in configs if cfg.main_db_id is not None}
            
            data = []
            for db in databases:
                cfg = config_map.get(db.id)
                data.append({
                    'database_id': db.id,
                    'database_name': db.database_name,
                    'description': db.description,
                    'networkPath': cfg.network_path if cfg else '',
                    'username': cfg.smb_username if cfg else '',
                    'password': '******' if (cfg and cfg.smb_password) else '',
                    'isActive': cfg.is_active if cfg else 0,
                    'hasConfig': cfg is not None
                })
            return JsonResponse({'status': 'success', 'data': data})
            
        elif request.method == 'POST':
            body = json.loads(request.body)
            db_id = body.get('database_id')
            if not db_id:
                return JsonResponse({'status': 'error', 'message': 'database_id is required'}, status=400)
                
            db = MainDatabase.objects.filter(id=db_id).first()
            if not db:
                return JsonResponse({'status': 'error', 'message': 'Database not found'}, status=404)
                
            with transaction.atomic():
                cfg = FileStorageConfig.objects.filter(main_db_id=db_id).first()
                if not cfg:
                    cfg = FileStorageConfig(main_db=db, name=db.database_name, protocol='smb', is_active=1)
                
                cfg.network_path = body.get('networkPath', '').strip()
                cfg.smb_username = body.get('username', '').strip()
                cfg.is_active = int(body.get('isActive', 1))
                
                password = body.get('password', '')
                if password and password != '******':
                    cfg.set_password(password)
                elif not password:
                    cfg.smb_password = None
                    
                cfg.save()
                
            create_user_log(user=request.user, action="Update Network Share Config", detail=f"Updated Network Share settings for DB {db.database_name} in DB", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Network share settings updated successfully.'})

        elif request.method == 'DELETE':
            body = json.loads(request.body or '{}')
            db_id = body.get('database_id')
            if not db_id:
                return JsonResponse({'status': 'error', 'message': 'database_id is required'}, status=400)
                
            with transaction.atomic():
                cfg = FileStorageConfig.objects.filter(main_db_id=db_id).first()
                if cfg:
                    cfg.delete()
                    
            create_user_log(user=request.user, action="Delete Network Share Config", detail=f"Deleted Network Share settings for DB ID {db_id}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Network share settings deleted successfully.'})
            
    except Exception as e:
        create_user_log(user=request.user, action="Update Network Share Config", detail=str(e), status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_action(PermissionIDs.SETTING_ACCESS)
def ApiMailSetting(request):
    try:
        from apps.setting.models import MailSetting
        config = MailSetting.objects.first()
        if not config:
            config = MailSetting()

        if request.method == 'GET':
            return JsonResponse({
                'status': 'success',
                'data': {
                    'host': config.host,
                    'port': config.port,
                    'tls': config.use_tls,
                    'fromEmail': config.from_email,
                    'username': config.host_user,
                    'password': '******' if config.host_password else '',
                    'backend': config.backend
                }
            })

        elif request.method == 'POST':
            data = json.loads(request.body)
            with transaction.atomic():
                db_config, created = MailSetting.objects.get_or_create(id=1)
                db_config.host = data.get('host', '').strip()
                try:
                    db_config.port = int(data.get('port', 587))
                except (ValueError, TypeError):
                    db_config.port = 587
                db_config.use_tls = bool(data.get('tls', True))
                db_config.from_email = data.get('fromEmail', '').strip()
                db_config.host_user = data.get('username', '').strip()
                db_config.backend = data.get('backend', 'django.core.mail.backends.smtp.EmailBackend').strip() or 'django.core.mail.backends.smtp.EmailBackend'
                
                password = data.get('password', '')
                if password and password != '******':
                    db_config.set_password(password)
                elif not password:
                    db_config.host_password = None
                
                db_config.save()

            create_user_log(user=request.user, action="Update Mail Config", detail="Updated Mail settings in DB", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Mail settings updated successfully.'})

    except Exception as e:
        create_user_log(user=request.user, action="Update Mail Config", detail=str(e), status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)