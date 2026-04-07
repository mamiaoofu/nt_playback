import json
from django.shortcuts import  redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from apps.core.utils.function import create_user_log, get_user_os_browser_architecture
from apps.core.utils.permissions import  require_action

from apps.home.models import SetColumnAudioRecord

@login_required
@require_GET
@require_action('Set Column','Audio Records')
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
@require_action('Set Column')
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
                create_user_log(user=user, action="Delete Column Audio Record", detail=f"Deleted: {name}", status="success", request=request)
                return JsonResponse({'status': 'success', 'message': 'Deleted successfully'})
            except SetColumnAudioRecord.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)

        elif action == 'toggle':
            record_id = data.get('id')
            use_status = data.get('use')
            
            try:
                record = SetColumnAudioRecord.objects.get(id=record_id, user=user)
            except SetColumnAudioRecord.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Record not found'}, status=404)
            
            if use_status:
                # Enable this one, disable others
                SetColumnAudioRecord.objects.filter(user=user).update(use=False)
                record.use = True
            else:
                record.use = False
            
            record.save()
            create_user_log(user=user, action="Toggle Column Audio Record", detail=f"Toggle use status: {record.name} -> {record.use}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': 'Status updated successfully'})

        # Common fields for create/update
        name = data.get('name', '').strip()
        description = data.get('description', '')
        raw_data = data.get('raw_data', '')

        if not name:
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
            create_user_log(user=user, action="Create Column Audio Record", detail=f"Created: {name}", status="success", request=request)
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
            
            create_user_log(user=user, action="Update Column Audio Record", detail=f"Updated: {name}", status="success", request=request)
            return JsonResponse({'status': 'success', 'message': f'Updated {name} successfully'})
        
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        create_user_log(user=request.user, action="Save Column Audio Record", detail=str(e), status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)