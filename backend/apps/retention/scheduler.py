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

    # Check if config or task was activated/saved today after the execution time.
    # If so, skip today's run to avoid executing immediately (wait for the next cycle).
    if config.execution_time:
        if config.updated_at:
            local_config_update = timezone.localtime(config.updated_at)
            if local_config_update.date() == now.date() and local_config_update.time() >= config.execution_time:
                return
        if task.updated_at:
            local_task_update = timezone.localtime(task.updated_at)
            if local_task_update.date() == now.date() and local_task_update.time() >= config.execution_time:
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
            retention_date=timezone.now(),
            retention_task_id=task.id,
            delete_option=config.delete_option
        )
        try:
            from apps.core.utils.function import create_user_log
            period_str = time_period_desc
            if period_str:
                import re
                period_str = re.sub(r'(?i)older than', 'Over', period_str)
                period_str = period_str.replace(' to ', ' - ')
            local_now = timezone.localtime(timezone.now())
            occurrence = 'Once' if config.is_once else 'Recurrence'
            delete_option_desc = "Indexes & Voice Files" if config.delete_option == 'VOICE_AND_INDEX' else "Indexes"
            detail_str = f"Retention ID : {task.id} | Retention Period : {period_str} | {occurrence} | {delete_option_desc} | Running Date : {local_now.strftime('%Y-%m-%d %H:%M')} | Index Count : {count}"
            
            create_user_log(
                user=None,
                action='Complete Soft Delete Schedule Retention',
                detail=detail_str,
                status='success',
                request=None,
                ip_address='127.0.0.1'
            )
            logger.info(f"Auto Retention UserLog created for task {task.id}. Count: {count}")
        except Exception as e:
            logger.error(f"Failed to create UserLog for Auto Retention task {task.id}: {e}")
    
    # Update the single AUTO_EXECUTION task
    task.status = 'RUNNING'
    task.index_count = count
    task.executed_at = timezone.now()
    task.time_period = time_period_desc
    task.save()
    logger.info(f"Auto Retention executed. Task {task.id} updated. Records affected: {count}")
    
    # Handle once-off task: disable active status if is_once
    if config.is_once:
        config.is_active = False
        config.save()
        logger.info("Schedule Retention set to Once has executed. Auto config disabled.")

def delete_audio_file_via_smb(main_db_id, file_path):
    from apps.home.models import FileStorageConfig
    from apps.home.views import parse_network_path, get_smb_relative_path
    from smb.SMBConnection import SMBConnection
    import socket
    
    def resolve_smb_host(hostname):
        try:
            return socket.gethostbyname(hostname)
        except Exception:
            return hostname

    config = None
    if main_db_id:
        config = FileStorageConfig.objects.filter(main_db_id=main_db_id, is_active=True).first()
    if not config:
        config = FileStorageConfig.objects.filter(is_active=True).first()
        
    if not config:
        logger.warning("No active storage configuration found for SMB deletion.")
        return False, "No active storage configuration found."
        
    parsed = parse_network_path(config.network_path)
    server = parsed['host']
    share = parsed['share']
    base_path = parsed['base_path']
    smb_user = config.smb_username
    smb_pass = config.get_password()
    
    if not server or not share:
        return False, f"Invalid network path parsed: Host={server}, Share={share}"
        
    rel_path = get_smb_relative_path(file_path, base_path)
    clean_path = '/' + rel_path.replace('\\', '/').lstrip('/')
    
    logger.info(f"Connecting to SMB to delete: {server}/{share}{clean_path} as user {smb_user}")
    
    client_name = 'nt_playback_scheduler'
    conn = None
    try:
        conn = SMBConnection(smb_user, smb_pass, client_name, server, use_ntlm_v2=True, is_direct_tcp=True)
        connected = conn.connect(resolve_smb_host(server), 445, timeout=10)
        if not connected:
            return False, f"Failed to connect to SMB server {server}"
            
        conn.deleteFiles(share, clean_path)
        logger.info(f"Successfully deleted file via SMB: {share}{clean_path}")
        return True, None
    except Exception as e:
        logger.error(f"SMB deletion error for {share}{clean_path}: {e}")
        return False, str(e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def execute_permanent_delete_job():
    print("execute_permanent_delete_job called!")
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
        
    print(f"execute_permanent_delete_job parameters: now={now}, val={val}, unit={unit}, cutoff_date={cutoff_date}")
    expired_records = AudioInfo.objects.filter(status=False, retention_date__lte=cutoff_date)
    print(f"execute_permanent_delete_job found expired records count: {expired_records.count()}")
    
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
            
            # success_by_db: db_name -> list of file_name
            success_by_db = {}
            # unsuccess_by_db: db_name -> list of (file_name, error_reason)
            unsuccess_by_db = {}
            
            total_attempted = len(records)
            success_indexes = 0
            success_voice = 0
            
            for record in records:
                db_name = record.main_db.database_name if record.main_db else 'Unknown'
                if db_name not in success_by_db:
                    success_by_db[db_name] = []
                if db_name not in unsuccess_by_db:
                    unsuccess_by_db[db_name] = []
                    
                if record.retention_task:
                    task_types.add(record.retention_task.task_type)
                if record.delete_option:
                    delete_options.add(record.delete_option)
                    
                file_name = record.audiofile.file_name if record.audiofile else "Unknown_File"
                
                try:
                    if record.delete_option == 'VOICE_AND_INDEX':
                        host_file_path = record.audiofile.file_path if record.audiofile else None
                        
                        deleted_voice = False
                        error_reason = None
                        
                        if not host_file_path:
                            error_reason = "No file path in database"
                        else:
                            from apps.home.views import map_host_to_container_path
                            # Combine host path and file name if host_file_path doesn't end with file_name
                            if file_name and not host_file_path.replace('/', '\\').rstrip('\\').lower().endswith(file_name.lower()):
                                separator = '\\' if '\\' in host_file_path or ':' in host_file_path else '/'
                                combined_host_path = host_file_path.rstrip('\\/') + separator + file_name
                            else:
                                combined_host_path = host_file_path
                                
                            container_file_path = map_host_to_container_path(combined_host_path)
                            
                            # First attempt: Try deleting locally (if local directory is mounted/accessible)
                            if container_file_path:
                                container_dir_path = os.path.dirname(container_file_path)
                                if container_dir_path and os.path.exists(container_dir_path):
                                    if os.path.exists(container_file_path):
                                        try:
                                            os.remove(container_file_path)
                                            logger.info(f"Successfully deleted physical file locally: {container_file_path}")
                                            deleted_voice = True
                                        except Exception as e:
                                            logger.warning(f"Failed to delete file locally {container_file_path}, will try SMB fallback: {e}")
                                            error_reason = f"Local delete failed: {str(e)}"
                                    else:
                                        # File doesn't exist locally, but directory exists. Let SMB handle it.
                                        pass
                            
                            # Second attempt: If not deleted locally, try deleting via SMB
                            if not deleted_voice:
                                main_db_id = record.main_db_id if record.main_db else None
                                success, err_msg = delete_audio_file_via_smb(main_db_id, combined_host_path)
                                if success:
                                    deleted_voice = True
                                else:
                                    error_reason = err_msg or "Unknown SMB error"
                                    
                        # Handle results of VOICE_AND_INDEX
                        if deleted_voice:
                            success_voice += 1
                            with transaction.atomic():
                                if record.audiofile:
                                    record.audiofile.delete()
                                record.delete()
                            success_indexes += 1
                            success_by_db[db_name].append(file_name)
                        else:
                            # It failed to delete physical file.
                            # Check if the error is "File not found" (which means the file is already gone)
                            is_file_not_found = False
                            if error_reason and any(x in error_reason for x in ["0xC0000034", "STATUS_NO_SUCH_FILE", "File not found", "does not exist", "No file path"]):
                                is_file_not_found = True
                                
                            if is_file_not_found:
                                # File doesn't exist on disk, so we delete DB record anyway to avoid infinite loop
                                try:
                                    with transaction.atomic():
                                        if record.audiofile:
                                            record.audiofile.delete()
                                        record.delete()
                                    success_indexes += 1
                                    unsuccess_by_db[db_name].append((file_name, error_reason))
                                except Exception as db_err:
                                    logger.error(f"Failed to delete DB record for missing file: {db_err}")
                            else:
                                # It's a real connection/permission error! We do NOT delete DB record so it will retry.
                                unsuccess_by_db[db_name].append((file_name, error_reason))
                                
                    else:
                        # INDEX_ONLY
                        with transaction.atomic():
                            if record.audiofile:
                                record.audiofile.delete()
                            record.delete()
                        success_indexes += 1
                        success_by_db[db_name].append(file_name)
                        
                except Exception as e:
                    logger.error(f"Failed to permanently delete record {record.id}: {e}")
            
            # Count actual successes and unsuccesses
            total_success = sum(len(files) for files in success_by_db.values())
            total_unsuccess = sum(len(files) for files in unsuccess_by_db.values())
            
            # Only write log file and save log entry if we actually processed something
            if total_success > 0 or total_unsuccess > 0:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Execute Date: {local_now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    if 'VOICE_AND_INDEX' in delete_options:
                        f.write(f"# Indexes & Voice Files - Complete {success_voice}/{total_attempted}\n")
                        f.write(f"# Indexes - {success_indexes}/{total_attempted}\n")
                        f.write(f"# Voice Files - {success_voice}/{total_attempted}\n\n\n")
                    else:
                        f.write(f"# Indexes - Complete {success_indexes}/{total_attempted}\n\n\n")
                        
                    f.write(f"# SUCCESS - {total_success}\n")
                    for db_name, files in success_by_db.items():
                        if files:
                            f.write(f"# Source Storage: {db_name}\n")
                            for name in files:
                                f.write(f"{name}\n")
                            f.write("\n")
                            
                    f.write("\n")
                    f.write(f"# UNSUCCESS - {total_unsuccess}\n")
                    for db_name, files in unsuccess_by_db.items():
                        if files:
                            f.write(f"# Source Storage: {db_name}\n")
                            for name, err in files:
                                f.write(f"{name} (Error: {err})\n")
                            f.write("\n")
                
                RetentionLog.objects.create(
                    task_type=",".join(task_types) if task_types else "SYSTEM",
                    delete_option=",".join(delete_options) if delete_options else "UNKNOWN",
                    index_count=success_indexes,
                    time_period=time_period_desc,
                    user_create="scheduler",
                    file_log_path=log_file,
                    status="SUCCESS"
                )
                logger.info(f"Permanent delete finished for task {task_id}. Succeeded: {total_success}, Failed: {total_unsuccess}. Log: {log_file}")
                
                # Create user logs
                task_obj = None
                if task_id:
                    try:
                        task_obj = RetentionTask.objects.get(pk=task_id)
                    except Exception:
                        pass
                        
                if task_obj and task_obj.task_type == 'AUTO_EXECUTION':
                    action_name = 'Complete Delete Schedule Retention'
                else:
                    action_name = 'Complete Delete Immediately Retention'
                    
                period_str = task_obj.time_period if task_obj and task_obj.time_period else time_period_desc
                if period_str:
                    import re
                    period_str = re.sub(r'(?i)older than', 'Over', period_str)
                    period_str = period_str.replace(' to ', ' - ')
                    
                occurrence = 'Once'
                if task_obj and task_obj.task_type == 'AUTO_EXECUTION':
                    try:
                        config_auto = AutoRetentionConfig.load()
                        occurrence = 'Once' if config_auto.is_once else 'Recurrence'
                    except Exception:
                        occurrence = 'Recurrence'
                        
                # Format delete_option_desc with success counts
                if 'VOICE_AND_INDEX' in delete_options:
                    delete_desc = f"Indexes & Voice Files ({success_voice}/{total_attempted})"
                else:
                    delete_desc = f"Indexes ({success_indexes}/{total_attempted})"
                    
                local_now_task = timezone.localtime(now)
                detail_str = f"Retention ID : {task_id} | Retention Period : {period_str} | {occurrence} | {delete_desc} | Running Date : {local_now_task.strftime('%Y-%m-%d %H:%M')} | Index Count : {success_indexes}"
                
                try:
                    from apps.core.utils.function import create_user_log
                    # 1. Log SUCCESS / summary log
                    create_user_log(
                        user=None,
                        action=action_name,
                        detail=detail_str,
                        status='success',
                        request=None,
                        ip_address='127.0.0.1'
                    )
                    
                    # 2. Log grouped ERRORS (if any unsuccesses occur)
                    if total_unsuccess > 0:
                        error_groups = {}
                        for db_name, files in unsuccess_by_db.items():
                            for name, err in files:
                                cat = "System Bug / Database Error"
                                if err:
                                    err_lower = err.lower()
                                    if any(x in err_lower for x in ["0xc0000034", "status_no_such_file", "file not found", "does not exist", "unreachable", "no file path"]):
                                        cat = "ไฟล์เสียงไม่พบในโฟลเดอร์ (File not found)"
                                    elif any(x in err_lower for x in ["permission denied", "access denied", "0xc0000022"]):
                                        cat = "ไม่มีสิทธิ์เข้าถึงโฟลเดอร์ หรือที่อยู่ผิด (Permission denied)"
                                    elif any(x in err_lower for x in ["timeout", "timed out", "connection refused", "cannot connect"]):
                                        cat = "การเชื่อมต่อขัดข้อง (Connection timeout / refused)"
                                    else:
                                        cat = f"ข้อผิดพลาดจากระบบ: {err}"
                                if cat not in error_groups:
                                    error_groups[cat] = []
                                error_groups[cat].append(name)
                                
                        detail_parts = [f"Retention ID : {task_id}"]
                        for cat, file_list in error_groups.items():
                            detail_parts.append(f"มี {len(file_list)} ไฟล์เกิดข้อผิดพลาด: {cat}")
                        detail_str_err = " | ".join(detail_parts)
                        
                        create_user_log(
                            user=None,
                            action=action_name,
                            detail=detail_str_err,
                            status='error',
                            request=None,
                            ip_address='127.0.0.1'
                        )
                except Exception as log_ex:
                    logger.error(f"Failed to create UserLog for permanent delete: {log_ex}")
        
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
