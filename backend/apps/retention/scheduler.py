import os
import logging
from datetime import timedelta, datetime
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.conf import settings
from .models import AutoRetentionConfig, RetentionTask, RetentionLog
from apps.core.model.audio.models import AudioInfo

from django.db import transaction

logger = logging.getLogger(__name__)

def execute_auto_retention_job():
    config = AutoRetentionConfig.load()
    if not config.is_active:
        return
        
    now = timezone.localtime(timezone.now())
    
    # 1. Check schedule constraints
    if config.how_often == 'daily':
        # Daily runs every day, no weekday check needed
        pass
    elif config.how_often == 'weekly':
        if config.what_day and now.strftime('%A') != config.what_day:
            return
    elif config.how_often == 'monthly':
        if config.what_day:
            if config.what_day.isdigit():
                target_day = int(config.what_day)
                import calendar
                _, last_day = calendar.monthrange(now.year, now.month)
                effective_target = min(target_day, last_day)
                if now.day != effective_target:
                    return
            else:
                # Fallback to weekday check in the first 7 days
                if now.strftime('%A') != config.what_day or now.day > 7:
                    return
    elif config.how_often == 'yearly':
        if config.what_day:
            if config.what_day.isdigit():
                target_day = int(config.what_day)
                import calendar
                # Run in January (month == 1)
                _, last_day = calendar.monthrange(now.year, 1)
                effective_target = min(target_day, last_day)
                if now.month != 1 or now.day != effective_target:
                    return
            else:
                # Fallback to weekday check in January
                if now.strftime('%A') != config.what_day or now.month != 1 or now.day > 7:
                    return
            
    if config.execution_time and now.time() < config.execution_time:
        return
        
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if RetentionTask.objects.filter(task_type='AUTO_EXECUTION', executed_at__gte=today_start).exists():
        return
        
    # Find the READY, RUNNING, SUCCESS, or RESTORED task
    task = RetentionTask.objects.filter(task_type='AUTO_EXECUTION', status__in=['READY', 'RUNNING', 'SUCCESS', 'RESTORED']).first()
    if not task:
        return
        
    cutoff_date = None
    time_period_desc = ""
    records = None
    
    # 2. Determine cutoff or date range based on retention_type
    if config.retention_type == 'OLDER_THAN':
        if config.older_than_type == 'RELATIVE':
            period = config.retention_period or "1Y"
            try:
                num = int(''.join(c for c in period if c.isdigit()))
                unit = ''.join(c for c in period if c.isalpha()).upper()
            except ValueError:
                num = 1
                unit = 'Y'
            
            if unit == 'D':
                cutoff_date = now - timedelta(days=num)
            elif unit == 'M':
                cutoff_date = now - timedelta(days=num*30)
            elif unit == 'Y':
                cutoff_date = now - timedelta(days=num*365)
            else:
                cutoff_date = now - timedelta(days=365)
            
            unit_str = 'Day' if unit == 'D' else 'Month' if unit == 'M' else 'Year'
            time_period_desc = f"Older than {num} {unit_str}{'s' if num > 1 else ''}"
        elif config.older_than_type == 'DATE' and config.older_than_date:
            cutoff_date = timezone.make_aware(datetime.combine(config.older_than_date, datetime.min.time()))
            time_period_desc = f"Older than {config.older_than_date}"
            
        if cutoff_date:
            records = AudioInfo.objects.filter(start_datetime__lt=cutoff_date, status=True)
            
    elif config.retention_type == 'DATE_RANGE':
        if config.start_date and config.end_date:
            start_dt = timezone.make_aware(datetime.combine(config.start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(config.end_date, datetime.max.time().replace(microsecond=999999)))
            records = AudioInfo.objects.filter(start_datetime__gte=start_dt, start_datetime__lte=end_dt, status=True)
            time_period_desc = f"{config.start_date} to {config.end_date}"
            
    if records is None:
        return

    count = records.count()
    
    if count > 0:
        records.update(
            status=False,
            retention_date=now,
            retention_task_id=task.id,
            delete_option=config.delete_option
        )
    
    # Update the single AUTO_EXECUTION task
    task.status = 'RUNNING'
    task.index_count = count
    task.executed_at = now
    task.time_period = time_period_desc
    task.save()
    logger.info(f"Auto Retention executed. Task {task.id} updated. Records affected: {count}")
    
    # Handle once-off task: disable active status if is_once
    if config.is_once:
        config.is_active = False
        config.save()
        logger.info("Schedule Retention set to Once has executed. Auto config disabled.")

def execute_permanent_delete_job():
    config = AutoRetentionConfig.load()
    val = config.permanent_delete_value
    unit = config.permanent_delete_unit
    
    now = timezone.now()
    if unit == 'minute':
        cutoff_date = now - timedelta(minutes=val)
        time_period_desc = f"{val} Minute{'s' if val > 1 else ''} Expired"
    else:
        cutoff_date = now - timedelta(days=val)
        time_period_desc = f"{val} Day{'s' if val > 1 else ''} Expired"
        
    expired_records = AudioInfo.objects.filter(status=False, retention_date__lte=cutoff_date)
    
    if expired_records.exists():
        # Group expired records by retention_task_id
        tasks_records = {}
        for record in expired_records.select_related('main_db', 'audiofile', 'retention_task'):
            task_id = record.retention_task_id or 0
            if task_id not in tasks_records:
                tasks_records[task_id] = []
            tasks_records[task_id].append(record)
            
        for task_id, records in tasks_records.items():
            log_path = os.path.join(settings.MEDIA_ROOT, 'retention_logs', f"{now.strftime('%Y-%m')}")
            os.makedirs(log_path, exist_ok=True)
            
            local_now = timezone.localtime(timezone.now())
            # Format: DataRetention_<retention id>_yyyymmdd_hhmmss.text
            log_filename = f"DataRetention_{task_id}_{local_now.strftime('%Y%m%d_%H%M%S')}.text"
            log_file = os.path.join(log_path, log_filename)
            
            task_types = set()
            delete_options = set()
            deleted_by_db = {}
            
            for record in records:
                db_name = record.main_db.database_name if record.main_db else 'Unknown'
                try:
                    with transaction.atomic():
                        # 1. Delete physical file first (if chosen)
                        if record.delete_option == 'VOICE_AND_INDEX' and record.audiofile and record.audiofile.file_path:
                            from apps.home.views import map_host_to_container_path
                            host_file_path = record.audiofile.file_path
                            file_name = record.audiofile.file_name or ""
                            
                            # Combine host path and file name if host_file_path doesn't end with file_name
                            if file_name and not host_file_path.replace('/', '\\').rstrip('\\').lower().endswith(file_name.lower()):
                                separator = '\\' if '\\' in host_file_path or ':' in host_file_path else '/'
                                combined_host_path = host_file_path.rstrip('\\/') + separator + file_name
                            else:
                                combined_host_path = host_file_path
                                
                            container_file_path = map_host_to_container_path(combined_host_path)
                            container_dir_path = os.path.dirname(container_file_path)
                            
                            # Check if the parent directory is accessible to detect offline storage
                            if container_dir_path and not os.path.exists(container_dir_path):
                                raise OSError(f"Storage directory {container_dir_path} is unreachable (offline).")
                                
                            if os.path.exists(container_file_path):
                                try:
                                    os.remove(container_file_path)
                                    logger.info(f"Successfully deleted physical file: {container_file_path}")
                                except Exception as e:
                                    raise OSError(f"Failed to delete physical file {container_file_path}: {e}")
                        
                        # 2. Delete from DB (tb_audiofile and tb_audioinfo)
                        file_name = record.audiofile.file_name if record.audiofile else "Unknown_File"
                        if record.audiofile:
                            record.audiofile.delete()
                        record.delete()
                    
                    # Transaction succeeded!
                    if db_name not in deleted_by_db:
                        deleted_by_db[db_name] = []
                    deleted_by_db[db_name].append(file_name)
                    
                    if record.retention_task:
                        task_types.add(record.retention_task.task_type)
                    if record.delete_option:
                        delete_options.add(record.delete_option)
                except Exception as e:
                    logger.error(f"Failed to permanently delete record {record.id}: {e}")
            
            # Only write log file and save log entry if we actually deleted something
            if deleted_by_db:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Execute Date: {local_now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    blocks = []
                    for db_name, file_names in deleted_by_db.items():
                        block = f"# Source Storage: {db_name}\n" + "".join(f"{name}\n" for name in file_names)
                        blocks.append(block)
                    f.write("\n".join(blocks))
                
                total_deleted = sum(len(names) for names in deleted_by_db.values())
                RetentionLog.objects.create(
                    task_type=",".join(task_types) if task_types else "SYSTEM",
                    delete_option=",".join(delete_options) if delete_options else "UNKNOWN",
                    index_count=total_deleted,
                    time_period=time_period_desc,
                    user_create="scheduler",
                    file_log_path=log_file,
                    status="SUCCESS"
                )
                logger.info(f"Permanent delete finished for task {task_id}. Records: {total_deleted}. Log: {log_file}")
        
    running_tasks = RetentionTask.objects.filter(status='RUNNING')
    for task in running_tasks:
        if not AudioInfo.objects.filter(retention_task_id=task.id).exists():
            if task.task_type == 'AUTO_EXECUTION':
                if config.is_once:
                    task.status = 'SUCCESS'
                else:
                    task.status = 'READY'
            else:
                task.status = 'SUCCESS'
            task.save()

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    scheduler.add_job(
        execute_auto_retention_job,
        'interval',
        seconds=10,
        id='auto_retention',
        name='auto_retention',
        jobstore='default',
        replace_existing=True
    )
    
    scheduler.add_job(
        execute_permanent_delete_job,
        'interval',
        minutes=1,
        id='permanent_delete',
        name='permanent_delete',
        jobstore='default',
        replace_existing=True
    )
    
    register_events(scheduler)
    scheduler.start()
    print("Retention Scheduler started!")
