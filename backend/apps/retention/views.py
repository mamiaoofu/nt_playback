from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q
from django.conf import settings
from .models import RetentionTask, RetentionLog, AutoRetentionConfig
from .serializers import RetentionTaskSerializer, RetentionLogSerializer, AutoRetentionConfigSerializer
from apps.core.model.audio.models import AudioInfo
from apps.core.utils.function import create_user_log
from apps.core.model.authorize.models import UserLog, UserProfile


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
        return f"{start} - {end}"
    return str(config.retention_period or '')


def _format_time_period_detail_from_task(task):
    if not task:
        return ""
    time_period = task.time_period or ''
    if ' to ' in time_period:
        start, end = time_period.split(' to ', 1)
        return f"{start} - {end}"
    if ' - ' in time_period and task.task_type == 'MANUAL':
        start, end = time_period.split(' - ', 1)
        return f"{start} - {end}"
    return time_period.replace('Older than', 'Over')


def _format_occurrence(task=None, config=None):
    if task and task.task_type == 'MANUAL':
        return 'Once'
    if config is not None:
        return 'Once' if config.is_once else 'Recurrence'
    return 'Recurrence'


def _build_log_detail(task_id, time_period, occurrence=None, delete_option=None, restore=False, running_date=None, index_count=None):
    detail_parts = [f"Retention ID : {task_id}", f"Retention Period : {time_period}"]
    if restore:
        detail_parts.append('Indexes')
    else:
        if occurrence:
            detail_parts.append(occurrence)
        if delete_option:
            detail_parts.append(_format_delete_option(delete_option))
            
    if running_date is not None:
        detail_parts.append(f"Running Date : {running_date}")
    if index_count is not None:
        detail_parts.append(f"Index Count : {index_count}")
        
    return ' | '.join(detail_parts)


def _clean_log_detail(detail_str):
    if not detail_str:
        return ''
    parts = [p.strip() for p in detail_str.split('|')]
    clean_parts = []
    for p in parts:
        if p.lower().startswith('running date :') or p.lower().startswith('index count :'):
            continue
        clean_parts.append(p)
    return ' | '.join(clean_parts)


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


def _verify_user_password(user, password):
    """
    Verify user password. For AD users, attempt LDAP/AD verification first.
    For non-AD users, use Django's check_password().
    Returns True if password is valid, False otherwise.
    """
    if not user or not user.is_authenticated:
        return False
    
    try:
        # Check if user is an AD user
        user_profile = UserProfile.objects.filter(user=user).first()
        if user_profile and user_profile.ad_account:
            # Try AD authentication
            try:
                from ldap3 import Server, Connection, NTLM, SIMPLE, ALL
                from ldap3.core.exceptions import LDAPBindError
                
                ad_server_uri = "ldap://192.168.1.8"
                username = user.username
                
                formats = [
                    (f"nichetel.local\\{username}", NTLM),
                    (f"nichetel\\{username}", NTLM),
                    (f"{username}@nichetel.local", SIMPLE)
                ]
                
                server = Server(ad_server_uri, get_info=ALL)
                
                for principal, auth_type in formats:
                    try:
                        conn = Connection(
                            server,
                            user=principal,
                            password=password,
                            authentication=auth_type,
                            auto_bind=True
                        )
                        conn.unbind()
                        return True  # AD authentication successful
                    except LDAPBindError:
                        continue
                    except Exception:
                        continue
                
                # All AD attempts failed, fall through to Django password check
                return user.check_password(password)
            except ImportError:
                # ldap3 not available, fall back to Django password check
                return user.check_password(password)
            except Exception:
                # Any other error, fall back to Django password check
                return user.check_password(password)
        else:
            # Non-AD user, use Django's check_password
            return user.check_password(password)
    except Exception:
        # Fallback to Django's check_password in case of any error
        return user.check_password(password) if user else False


def _calculate_next_run(task, config):
    if not task or task.task_type == 'MANUAL' or not config:
        return '-'
        
    execution_time = config.execution_time or datetime.strptime('01:00:00', '%H:%M:%S').time()
    now = timezone.localtime(timezone.now())
    
    last_executed_today = False
    if task.executed_at:
        exec_date = timezone.localtime(task.executed_at)
        if exec_date.date() == now.date():
            last_executed_today = True
            
    candidate = now.replace(hour=execution_time.hour, minute=execution_time.minute, second=0, microsecond=0)
    if candidate <= now or last_executed_today:
        candidate += timedelta(days=1)
        
    how_often = config.how_often or 'daily'
    what_day = config.what_day
    
    import calendar
    for _ in range(400):
        matches = False
        day_of_week = candidate.strftime('%A')
        
        if how_often == 'daily':
            matches = True
        elif how_often == 'weekly':
            if what_day and day_of_week.lower() == what_day.lower():
                matches = True
        elif how_often == 'monthly':
            if what_day:
                if what_day.isdigit():
                    target_day = int(what_day)
                    _, last_day = calendar.monthrange(candidate.year, candidate.month)
                    effective_target = min(target_day, last_day)
                    if candidate.day == effective_target:
                        matches = True
                else:
                    if day_of_week.lower() == what_day.lower() and candidate.day <= 7:
                        matches = True
        elif how_often == 'yearly':
            if candidate.month == 1 and what_day:
                if what_day.isdigit():
                    target_day = int(what_day)
                    _, last_day = calendar.monthrange(candidate.year, 1)
                    effective_target = min(target_day, last_day)
                    if candidate.day == effective_target:
                        matches = True
                else:
                    if day_of_week.lower() == what_day.lower() and candidate.day <= 7:
                        matches = True
                        
        if matches:
            return candidate.strftime('%Y-%m-%d %H:%M')
        candidate += timedelta(days=1)
        
    return '-'


class RetentionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def manual(self, request):
        # POST request
        action_name = 'Complete Soft Delete Immediately Retention'
        password = request.data.get('password')
        if not password:
            _create_error_log(request, action_name, 'Password is required')
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated or not _verify_user_password(request.user, password):
            _create_error_log(request, action_name, 'Invalid password')
            return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        start_date_str = request.data.get('date_range_start')
        end_date_str = request.data.get('date_range_end')
        delete_option = request.data.get('delete_option', 'INDEX_ONLY')
        user_create = request.user.username if request.user.is_authenticated else 'system'
        
        if not start_date_str or not end_date_str:
            _create_error_log(request, action_name, 'Missing date range')
            return Response({'error': 'Missing date range'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError as e:
            _create_error_log(request, action_name, 'Invalid date format (YYYY-MM-DD)', exception=e)
            return Response({'error': 'Invalid date format (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.db.models import Max
            max_id = RetentionTask.objects.aggregate(Max('id'))['id__max'] or 0
            next_id = max(max_id + 1, 10002)
            
            # Create Task
            task = RetentionTask.objects.create(
                id=next_id,
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

            running_date_str = timezone.localtime(task.created_at).strftime('%Y-%m-%d %H:%M') if task.created_at else '-'
            detail_str = f"Retention ID : {task.id} | Retention Period : {task.time_period} | Indexes | Running Date : {running_date_str} | Index Count : {count}"
            create_user_log(
                user=request.user,
                action=action_name,
                detail=detail_str,
                status='success',
                request=request
            )
            
            return Response({'message': 'Manual retention triggered', 'task_id': task.id, 'count': count})
        except Exception as e:
            return _error_response(request, action_name, f'Manual retention failed: {str(e)}', exception=e)

    @action(detail=False, methods=['get', 'put'])
    def auto(self, request):
        config = AutoRetentionConfig.load()
        if request.method == 'GET':
            is_running = RetentionTask.objects.filter(task_type='AUTO_EXECUTION', status='RUNNING').exists()
            data = AutoRetentionConfigSerializer(config).data
            data['is_running'] = is_running
            return Response(data)
        
        # PUT request
        is_permanent_delete_save = 'permanent_delete_value' in request.data
        action_name = 'Change Retention Permanent Delete' if is_permanent_delete_save else 'Save and Run Schedule Retention'

        password = request.data.get('password')
        if not password:
            _create_error_log(request, action_name, 'Password is required')
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated or not _verify_user_password(request.user, password):
            _create_error_log(request, action_name, 'Invalid password')
            return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if there is an active running task
        if RetentionTask.objects.filter(task_type='AUTO_EXECUTION', status__in=['READY', 'RUNNING']).exists():
            _create_error_log(request, action_name, 'Cannot edit configuration while a task is active (Ready or Running).')
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
                    task.update_by = request.user.username if request.user.is_authenticated else 'system'
                    task.save()
                else:
                    task = RetentionTask.objects.create(
                        id=10001,
                        task_type='AUTO_EXECUTION',
                        delete_option=config.delete_option or 'INDEX_ONLY',
                        status='READY' if config.is_active else 'STOPPED',
                        time_period=time_period_desc,
                        user_create=request.user.username if request.user.is_authenticated else 'system',
                        update_by=request.user.username if request.user.is_authenticated else 'system'
                    )

                if is_permanent_delete_save:
                    create_user_log(
                        user=request.user,
                        action='Change Retention Permanent Delete',
                        detail=f"Permanent Delete : {config.permanent_delete_value} {config.permanent_delete_unit}",
                        status='success',
                        request=request
                    )
                else:
                    period_str = time_period_desc
                    if period_str:
                        import re
                        period_str = re.sub(r'(?i)older than', 'over', period_str)
                        period_str = period_str.replace(' to ', ' - ')
                    
                    occurrence = _format_occurrence(config=config)
                    occurrence = 'Once' if occurrence == 'Once' else 'Recurrence'
                    delete_option_desc = "Indexes & Voice Files" if config.delete_option == 'VOICE_AND_INDEX' else "Indexes"
                    next_run_str = _calculate_next_run(task, config)
                    detail_str = f"Retention ID : {task.id} | Retention Period : {period_str} | {occurrence} | {delete_option_desc} | Running Date : {next_run_str} | Index Count : {task.index_count}"
                    
                    create_user_log(
                        user=request.user,
                        action='Save and Run Schedule Retention',
                        detail=detail_str,
                        status='success',
                        request=request
                    )

                return Response(serializer.data)
            _create_error_log(request, action_name, f"Invalid auto retention config: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return _error_response(request, action_name, f'Failed to save auto retention config: {str(e)}', exception=e)

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
        if not request.user.is_authenticated or not _verify_user_password(request.user, password):
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
            task.index_count = count
            task.update_by = request.user.username if request.user.is_authenticated else 'system'
            task.save()

            config = AutoRetentionConfig.load() if task.task_type == 'AUTO_EXECUTION' else None

            period_str = task.time_period or ''
            if period_str:
                import re
                period_str = re.sub(r'(?i)older than', 'over', period_str)
                period_str = period_str.replace(' to ', ' - ')
            
            running_date_str = timezone.localtime(task.created_at).strftime('%Y-%m-%d %H:%M') if task.task_type == 'MANUAL' else _calculate_next_run(task, config)
            detail_str = f"Retention ID : {task.id} | Retention Period : {period_str} | Indexes | Running Date : {running_date_str} | Index Count : {count}"
            
            create_user_log(
                user=request.user,
                action='Restore Data Schedule Retention' if task.task_type == 'AUTO_EXECUTION' else 'Restore Data Immediately Retention',
                detail=detail_str,
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
            task.update_by = request.user.username if request.user.is_authenticated else 'system'
            task.save()

            # Sync config is_active to True
            config = AutoRetentionConfig.load()
            config.is_active = True
            config.save()

            period_str = _format_time_period_detail_from_config(config)
            if period_str:
                import re
                period_str = re.sub(r'(?i)older than', 'over', period_str)
                period_str = period_str.replace(' to ', ' - ')
            occurrence = _format_occurrence(task=task, config=config)
            occurrence = 'Once' if occurrence == 'Once' else 'Recurrence'
            delete_option_desc = "Indexes & Voice Files" if config.delete_option == 'VOICE_AND_INDEX' else "Indexes"
            next_run_str = _calculate_next_run(task, config)
            detail_str = f"Retention ID : {task.id} | Retention Period : {period_str} | {occurrence} | {delete_option_desc} | Running Date : {next_run_str} | Index Count : {task.index_count}"
            
            create_user_log(
                user=request.user,
                action='Run Schedule Retention',
                detail=detail_str,
                status='success',
                request=request
            )

            return Response({'message': 'Task started', 'status': task.status})
        except Exception as e:
            return _error_response(request, 'Run Schedule Retention', f'Failed to start schedule retention: {str(e)}', exception=e)

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
            task.update_by = request.user.username if request.user.is_authenticated else 'system'
            task.save()

            # Sync config is_active to False
            config = AutoRetentionConfig.load()
            config.is_active = False
            config.save()

            period_str = _format_time_period_detail_from_config(config)
            if period_str:
                import re
                period_str = re.sub(r'(?i)older than', 'over', period_str)
                period_str = period_str.replace(' to ', ' - ')
            occurrence = _format_occurrence(task=task, config=config)
            occurrence = 'Once' if occurrence == 'Once' else 'Recurrence'
            delete_option_desc = "Indexes & Voice Files" if config.delete_option == 'VOICE_AND_INDEX' else "Indexes"
            detail_str = f"Retention ID : {task.id} | Retention Period : {period_str} | {occurrence} | {delete_option_desc} | Running Date : Stopped | Index Count : {task.index_count}"
            
            create_user_log(
                user=request.user,
                action='Stop Schedule Retention',
                detail=detail_str,
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
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 25))
        search_value = request.GET.get("search[value]", "").strip()
        action_filter = request.GET.get("action")
        running_date = request.GET.get("running_date")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        sort_field = request.GET.get("sort[0][field]")
        sort_dir = (request.GET.get("sort[0][dir]", "asc")).lower()

        retention_actions = [
            'Save and Run Immediately Retention',
            'Save and Run Schedule Retention',
            'Run Schedule Retention',
            'Stop Schedule Retention',
            'Restore Data Schedule Retention',
            'Restore Data Immediately Retention',
            'Auto Execution Schedule Retention',
            'Change Retention Permanent Delete',
            'Complete Delete Immediately Retention',
            'Complete Delete Schedule Retention',
            'Complete Soft Delete Schedule Retention',
            'Complete Soft Delete Immediately Retention',
        ]
        
        # Base query
        log_list = UserLog.objects.filter(
            action__in=retention_actions
        ).exclude(status='error').select_related('user')

        # Records total
        records_total = log_list.count()

        # Apply action filter
        if action_filter:
            acts = [a.strip() for a in action_filter.split(',') if a.strip()]
            if acts:
                log_list = log_list.filter(action__in=acts)

        # Helper to parse datetime
        def _parse_datetime(val):
            if not val:
                return None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(val, fmt)
                    if settings.USE_TZ and dt.tzinfo is None:
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    return dt
                except Exception:
                    pass
            return None

        # Apply from_date / to_date filters (against timestamp)
        if from_date:
            dt_from = _parse_datetime(from_date)
            if dt_from:
                log_list = log_list.filter(timestamp__gte=dt_from)
        if to_date:
            dt_to = _parse_datetime(to_date)
            if dt_to:
                log_list = log_list.filter(timestamp__lte=dt_to)

        # Apply running_date filter (starts with / icontains)
        if running_date:
            log_list = log_list.filter(detail__icontains=f"Running Date : {running_date}")

        # Apply search_value (multi-column)
        if search_value:
            tokens = [t.strip() for t in search_value.split(',') if t.strip()]
            if tokens:
                q_search = Q()
                for tok in tokens:
                    q_tok = (Q(user__username__icontains=tok) |
                             Q(action__icontains=tok) |
                             Q(detail__icontains=tok) |
                             Q(ip_address__icontains=tok) |
                             Q(client_type__icontains=tok))
                    q_search &= q_tok
                log_list = log_list.filter(q_search)

        # Records filtered count
        records_filtered = log_list.count()

        # Fetch records and build data (parse fields)
        config = AutoRetentionConfig.load()
        data = []
        
        for log in log_list:
            detail_str = log.detail or ''
            retention_id = '-'
            retention_period = '-'
            times = '-'
            delete_option = '-'
            running_date_val = '-'
            index_count = '-'
            
            parts = [p.strip() for p in detail_str.split('|')]
            for p in parts:
                if p.lower().startswith('retention id :'):
                    retention_id = p.split(':', 1)[1].strip()
                elif p.lower().startswith('retention period :'):
                    retention_period = p.split(':', 1)[1].strip()
                    import re
                    retention_period = re.sub(r':\d{2}\b', '', retention_period)
                elif p in ['Once', 'Recurrence']:
                    times = p
                elif p in ['Indexes & Voice Files', 'Indexes', 'Only Indexs', 'Indexs', 'Indexes & Voice Files']:
                    delete_option = p
                elif p.lower().startswith('running date :'):
                    running_date_val = p.split(':', 1)[1].strip()
                elif p.lower().startswith('index count :'):
                    index_count = p.split(':', 1)[1].strip()
            
            task_type = '-'
            task_update_by = None
            
            if retention_id.isdigit():
                task_id = int(retention_id)
                try:
                    task = RetentionTask.objects.get(pk=task_id)
                    task_type = 'Schedule' if task.task_type == 'AUTO_EXECUTION' else 'Immediately'
                    task_update_by = task.update_by or task.user_create
                    
                    if index_count == '-':
                        # Fallback for old logs
                        ret_logs = RetentionLog.objects.filter(file_log_path__icontains=f"DataRetention_{task_id}_")
                        if ret_logs.exists():
                            index_count = sum(r.index_count for r in ret_logs if r.index_count is not None)
                        else:
                            index_count = task.index_count
                    
                    if running_date_val == '-':
                        # Fallback for old logs
                        if task.task_type == 'MANUAL':
                            running_date_val = timezone.localtime(task.created_at).strftime('%Y-%m-%d %H:%M') if task.created_at else '-'
                        else:
                            running_date_val = _calculate_next_run(task, config)
                except RetentionTask.DoesNotExist:
                    pass
            
            if task_type == '-':
                if 'Schedule' in log.action:
                    task_type = 'Schedule'
                elif 'Immediately' in log.action:
                    task_type = 'Immediately'
                    
            download_url = None
            if log.action in ['Complete Delete Schedule Retention', 'Complete Delete Immediately Retention']:
                if retention_id.isdigit():
                    task_id = int(retention_id)
                    ret_log = RetentionLog.objects.filter(file_log_path__icontains=f"DataRetention_{task_id}_").first()
                    if ret_log:
                        download_url = f"/api/v1/retention/logs/{ret_log.id}/download/"
            
            ts_str = '-'
            if log.timestamp:
                ts_str = timezone.localtime(log.timestamp).strftime('%Y-%m-%d %H:%M')
                
            created_by_val = log.user.username if log.user else "-"
            if task_type == 'Schedule' and task_update_by:
                created_by_val = task_update_by

            client_type_val = log.client_type or "-"
            if log.action in ['Complete Soft Delete Schedule Retention', 'Change Retention Permanent Delete']:
                client_type_val = 'Server'

            data.append({
                "id": log.id,
                "retention_id": retention_id,
                "action": log.action,
                "retention_type": task_type,
                "retention_period": retention_period,
                "times": times,
                "index_count": index_count,
                "running_date": running_date_val,
                "created_by": created_by_val,
                "description": _clean_log_detail(log.detail),
                "ip_address": log.ip_address or "-",
                "timestamp": ts_str,
                "client_type": client_type_val,
                "download_url": download_url
            })

        # Python-level Sorting
        if sort_field and sort_dir:
            is_desc = sort_dir == 'desc'
            if sort_field == 'index_count':
                def _get_index_count(x):
                    val = x.get('index_count', '-')
                    if val == '-' or val is None or str(val).strip() == '':
                        return -1
                    try:
                        return int(val)
                    except ValueError:
                        return -1
                data.sort(key=_get_index_count, reverse=is_desc)
            elif sort_field == 'retention_id':
                def _get_retention_id(x):
                    val = x.get('retention_id', '-')
                    try:
                        return int(val)
                    except ValueError:
                        return -1
                data.sort(key=_get_retention_id, reverse=is_desc)
            elif sort_field in ['action', 'retention_type', 'retention_period', 'times', 'running_date', 'created_by', 'description', 'ip_address', 'timestamp', 'client_type']:
                data.sort(key=lambda x: str(x.get(sort_field, '')).lower(), reverse=is_desc)
        else:
            # Default order by timestamp descending
            data.sort(key=lambda x: str(x.get('timestamp', '')), reverse=True)

        # Python-level Slicing (Pagination)
        paginated_data = data[start:start + length]

        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": paginated_data
        })


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
