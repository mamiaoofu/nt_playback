from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
from .models import RetentionTask, RetentionLog, AutoRetentionConfig
from .serializers import RetentionTaskSerializer, RetentionLogSerializer, AutoRetentionConfigSerializer
from apps.core.model.audio.models import AudioInfo
from apps.core.utils.function import create_user_log


def _format_delete_option(delete_option):
    return "Indexes & Voice Files" if delete_option == 'VOICE_AND_INDEX' else "Indexes"


def _format_time_period_detail_from_config(config):
    if not config:
        return ""
    if config.retention_type == 'OLDER_THAN':
        if config.older_than_type == 'RELATIVE':
            period = config.retention_period or "1Y"
            num = ''.join(c for c in period if c.isdigit()) or '1'
            unit = ''.join(c for c in period if c.isalpha()).upper()
            unit_str = 'Day' if unit == 'D' else 'Month' if unit == 'M' else 'Year'
            return f"Over {num} {unit_str}{'s' if int(num) > 1 else ''}"
        return f"Over {config.older_than_date}"
    if config.retention_type == 'DATE_RANGE':
        start = str(config.start_date or '')
        end = str(config.end_date or '')
        return f"{start} 00:00:00 - {end} 23:59:59"
    return str(config.retention_period or '')


def _format_time_period_detail_from_task(task):
    if not task:
        return ""
    time_period = task.time_period or ''
    if ' to ' in time_period:
        start, end = time_period.split(' to ', 1)
        return f"{start} 00:00:00 - {end} 23:59:59"
    if ' - ' in time_period and task.task_type == 'MANUAL':
        start, end = time_period.split(' - ', 1)
        return f"{start} 00:00:00 - {end} 23:59:59"
    return time_period.replace('Older than', 'Over')


def _format_occurrence(task=None, config=None):
    if task and task.task_type == 'MANUAL':
        return 'Once'
    if config is not None:
        return 'Once' if config.is_once else 'Recurrence'
    return 'Recurrence'


def _build_log_detail(task_id, time_period, occurrence=None, delete_option=None, restore=False):
    detail_parts = [f"Retention ID : {task_id}", f"Retention Period : {time_period}"]
    if restore:
        detail_parts.append('Indexes')
    else:
        if occurrence:
            detail_parts.append(occurrence)
        if delete_option:
            detail_parts.append(_format_delete_option(delete_option))
    return ' | '.join(detail_parts)


def _create_error_log(request, action, detail, exception=None):
    create_user_log(
        user=request.user,
        action=action,
        detail=detail,
        status='error',
        request=request,
        exception=exception
    )


def _error_response(request, action, detail, exception=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR):
    _create_error_log(request, action, detail, exception=exception)
    return Response({'error': detail}, status=status_code)


class RetentionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def manual(self, request):
        password = request.data.get('password')
        if not password:
            _create_error_log(request, 'Save and Run Immediately Retention', 'Password is required')
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated or not request.user.check_password(password):
            _create_error_log(request, 'Save and Run Immediately Retention', 'Invalid password')
            return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        start_date_str = request.data.get('date_range_start')
        end_date_str = request.data.get('date_range_end')
        delete_option = request.data.get('delete_option', 'INDEX_ONLY')
        user_create = request.user.username if request.user.is_authenticated else 'system'
        
        if not start_date_str or not end_date_str:
            _create_error_log(request, 'Save and Run Immediately Retention', 'Missing date range')
            return Response({'error': 'Missing date range'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError as e:
            _create_error_log(request, 'Save and Run Immediately Retention', 'Invalid date format (YYYY-MM-DD)', exception=e)
            return Response({'error': 'Invalid date format (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create Task
            task = RetentionTask.objects.create(
                task_type='MANUAL',
                delete_option=delete_option,
                status='RUNNING',
                time_period=f"{start_date_str} - {end_date_str}",
                user_create=user_create
            )
            
            # Find audio records
            records = AudioInfo.objects.filter(
                start_datetime__gte=start_date,
                start_datetime__lte=end_date,
                status=True
            )
            count = records.count()
            
            # Soft Delete (Bulk Update)
            records.update(
                status=False,
                retention_date=timezone.now(),
                retention_task_id=task.id,
                delete_option=delete_option
            )
            
            # Update Task
            task.status = 'RUNNING'
            task.index_count = count
            task.save()

            create_user_log(
                user=request.user,
                action='Save and Run Immediately Retention',
                detail=_build_log_detail(
                    task.id,
                    _format_time_period_detail_from_task(task),
                    occurrence='Once',
                    delete_option=delete_option
                ),
                status='success',
                request=request
            )
            
            return Response({'message': 'Manual retention triggered', 'task_id': task.id, 'count': count})
        except Exception as e:
            return _error_response(request, 'Save and Run Immediately Retention', f'Manual retention failed: {str(e)}', exception=e)

    @action(detail=False, methods=['get', 'put'])
    def auto(self, request):
        config = AutoRetentionConfig.load()
        if request.method == 'GET':
            is_running = RetentionTask.objects.filter(task_type='AUTO_EXECUTION', status='RUNNING').exists()
            data = AutoRetentionConfigSerializer(config).data
            data['is_running'] = is_running
            return Response(data)
        
        # PUT request
        password = request.data.get('password')
        if not password:
            _create_error_log(request, 'Save and Run Schedule Retention', 'Password is required')
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated or not request.user.check_password(password):
            _create_error_log(request, 'Save and Run Schedule Retention', 'Invalid password')
            return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if there is an active running task
        if RetentionTask.objects.filter(task_type='AUTO_EXECUTION', status__in=['READY', 'RUNNING']).exists():
            _create_error_log(request, 'Save and Run Schedule Retention', 'Cannot edit configuration while a task is active (Ready or Running).')
            return Response({'error': 'Cannot edit configuration while a task is active (Ready or Running).'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AutoRetentionConfigSerializer(config, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                config = serializer.save(user_update=request.user.username if request.user.is_authenticated else 'system')
                
                # Calculate time_period_desc
                time_period_desc = ""
                if config.retention_type == 'OLDER_THAN':
                    if config.older_than_type == 'RELATIVE':
                        period = config.retention_period or "1Y"
                        try:
                            num = int(''.join(c for c in period if c.isdigit()))
                            unit = ''.join(c for c in period if c.isalpha()).upper()
                        except ValueError:
                            num = 1
                            unit = 'Y'
                        unit_str = 'Day' if unit == 'D' else 'Month' if unit == 'M' else 'Year'
                        time_period_desc = f"Older than {num} {unit_str}{'s' if num > 1 else ''}"
                    else:
                        time_period_desc = f"Older than {config.older_than_date}"
                elif config.retention_type == 'DATE_RANGE':
                    time_period_desc = f"{config.start_date} to {config.end_date}"

                task = RetentionTask.objects.filter(task_type='AUTO_EXECUTION').first()
                if task:
                    task.delete_option = config.delete_option or 'INDEX_ONLY'
                    task.time_period = time_period_desc
                    if config.is_active:
                        task.status = 'READY'
                        task.executed_at = None
                        task.index_count = 0
                    else:
                        task.status = 'STOPPED'
                    task.save()
                else:
                    task = RetentionTask.objects.create(
                        task_type='AUTO_EXECUTION',
                        delete_option=config.delete_option or 'INDEX_ONLY',
                        status='READY' if config.is_active else 'STOPPED',
                        time_period=time_period_desc,
                        user_create=request.user.username if request.user.is_authenticated else 'system'
                    )

                create_user_log(
                    user=request.user,
                    action='Save and Run Schedule Retention',
                    detail=_build_log_detail(
                        task.id,
                        time_period_desc.replace('Older than', 'Over'),
                        occurrence=_format_occurrence(config=config),
                        delete_option=config.delete_option
                    ),
                    status='success',
                    request=request
                )

                return Response(serializer.data)
            _create_error_log(request, 'Save and Run Schedule Retention', f"Invalid auto retention config: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return _error_response(request, 'Save and Run Schedule Retention', f'Failed to save auto retention config: {str(e)}', exception=e)

    @action(detail=False, methods=['get'])
    def tasks(self, request):
        tasks = RetentionTask.objects.all().order_by('-created_at')
        serializer = RetentionTaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        password = request.data.get('password')
        if not password:
            _create_error_log(request, 'Restore Data Schedule Retention' if pk else 'Restore Data Immediately Retention', 'Password is required')
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated or not request.user.check_password(password):
            _create_error_log(request, 'Restore Data Schedule Retention' if pk else 'Restore Data Immediately Retention', 'Invalid password')
            return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = RetentionTask.objects.get(pk=pk)
        except RetentionTask.DoesNotExist:
            _create_error_log(request, 'Restore Data Schedule Retention', f'Task not found: {pk}')
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            records = AudioInfo.objects.filter(retention_task_id=task.id, status=False)
            count = records.count()
            
            records.update(
                status=True,
                retention_date=None,
                retention_task_id=None,
                delete_option=None
            )
            
            task.status = 'RESTORED'
            task.executed_at = None
            task.index_count = 0
            task.save()

            create_user_log(
                user=request.user,
                action='Restore Data Schedule Retention' if task.task_type == 'AUTO_EXECUTION' else 'Restore Data Immediately Retention',
                detail=_build_log_detail(
                    task.id,
                    _format_time_period_detail_from_task(task),
                    restore=True
                ),
                status='success',
                request=request
            )
            
            return Response({'message': 'Data restored successfully', 'restored_count': count})
        except Exception as e:
            return _error_response(request, 'Restore Data Schedule Retention', f'Restore retention failed: {str(e)}', exception=e)

    @action(detail=True, methods=['post'], url_path='start')
    def start_task(self, request, pk=None):
        try:
            task = RetentionTask.objects.get(pk=pk)
        except RetentionTask.DoesNotExist:
            _create_error_log(request, 'Run Schedule Retention', f'Task not found: {pk}')
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if task.task_type != 'AUTO_EXECUTION':
            _create_error_log(request, 'Run Schedule Retention', f'Only auto-execution tasks can be started or stopped: {pk}')
            return Response({'error': 'Only auto-execution tasks can be started or stopped'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            task.status = 'READY'
            task.index_count = 0
            task.executed_at = None
            task.save()

            # Sync config is_active to True
            config = AutoRetentionConfig.load()
            config.is_active = True
            config.save()

            create_user_log(
                user=request.user,
                action='Run Schedule Retention',
                detail=_build_log_detail(
                    task.id,
                    _format_time_period_detail_from_config(config),
                    occurrence=_format_occurrence(task=task, config=config),
                    delete_option=config.delete_option
                ),
                status='success',
                request=request
            )

            return Response({'message': 'Task started', 'status': task.status})
        except Exception as e:
            return _error_response(request, 'Run Schedule Retention', f'Failed to start schedule retention: {str(e)}', exception=e)

        create_user_log(
            user=request.user,
            action='Run Schedule Retention',
            detail=_build_log_detail(
                task.id,
                _format_time_period_detail_from_config(config),
                occurrence=_format_occurrence(task=task, config=config),
                delete_option=config.delete_option
            ),
            status='success',
            request=request
        )

        return Response({'message': 'Task started', 'status': task.status})

    @action(detail=True, methods=['post'], url_path='stop')
    def stop_task(self, request, pk=None):
        try:
            task = RetentionTask.objects.get(pk=pk)
        except RetentionTask.DoesNotExist:
            _create_error_log(request, 'Stop Schedule Retention', f'Task not found: {pk}')
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if task.task_type != 'AUTO_EXECUTION':
            _create_error_log(request, 'Stop Schedule Retention', f'Only auto-execution tasks can be started or stopped: {pk}')
            return Response({'error': 'Only auto-execution tasks can be started or stopped'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            task.status = 'STOPPED'
            task.save()

            # Sync config is_active to False
            config = AutoRetentionConfig.load()
            config.is_active = False
            config.save()

            create_user_log(
                user=request.user,
                action='Stop Schedule Retention',
                detail=_build_log_detail(
                    task.id,
                    _format_time_period_detail_from_config(config)
                ),
                status='success',
                request=request
            )

            return Response({'message': 'Task stopped', 'status': task.status})
        except Exception as e:
            return _error_response(request, 'Stop Schedule Retention', f'Failed to stop schedule retention: {str(e)}', exception=e)

    @action(detail=False, methods=['get'], url_path='run_migrations')
    def run_migrations(self, request):
        from django.core.management import call_command
        try:
            call_command('migrate', interactive=False)
            return Response({'status': 'success', 'message': 'Migrations executed successfully'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def logs(self, request):
        logs = RetentionLog.objects.all().order_by('-created_at')
        serializer = RetentionLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download_log(self, request, pk=None):
        try:
            log = RetentionLog.objects.get(pk=pk)
        except RetentionLog.DoesNotExist:
            return Response({'error': 'Log not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not log.file_log_path:
            return Response({'error': 'File path is empty'}, status=status.HTTP_400_BAD_REQUEST)
            
        import os
        from django.http import FileResponse
        if os.path.exists(log.file_log_path):
            return FileResponse(open(log.file_log_path, 'rb'), as_attachment=True)
        return Response({'error': 'File not found on disk'}, status=status.HTTP_404_NOT_FOUND)
