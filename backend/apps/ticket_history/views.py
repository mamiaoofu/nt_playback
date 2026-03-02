from django.shortcuts import  redirect
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.core.mail import send_mail

from datetime import datetime
import base64
import socket
from datetime import datetime, timedelta
from django.utils import timezone
from datetime import timedelta
from django.middleware.csrf import get_token
from django.conf import settings
from apps.core.utils.function import create_user_log

from apps.core.utils.permissions import get_user_actions, require_action
# models
from apps.core.model.authorize.models import UserAuth,MainDatabase,SetAudio,UserProfile,Agent,UserFileShare
from apps.core.model.audio.models import AudioInfo

def ApiGetTicketHistory(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "").strip()
    
    email = request.POST.get("email") or request.GET.get("email")
    create_by = request.POST.get("create_by") or request.GET.get("create_by")
    user_name = request.POST.get("user_name") or request.GET.get("user_name")
    ticket_id = request.POST.get("ticket_id") or request.GET.get("ticket_id")
    
    start_date = request.POST.get("start_date") or request.GET.get("start_date")
    end_date = request.POST.get("end_date") or request.GET.get("end_date")
    files_audio = request.POST.get("files_audio") or request.GET.get("files_audio")
    status = request.POST.get("status") or request.GET.get("status")
    
    
    ticket_history_list = UserFileShare.objects.filter(type="ticket")
    records_total = ticket_history_list.count()
    
    # filter by ticket_id (frontend sends comma-separated values)
    if ticket_id:
        try:
            # split comma-separated values and ignore 'all'
            tokens = [t.strip() for t in str(ticket_id).split(',') if t and t.strip() and t.strip().lower() != 'all']
            if tokens:
                ticket_history_list = ticket_history_list.filter(code__in=tokens)
        except Exception:
            pass

    if start_date:
        ticket_history_list = ticket_history_list.filter(created_at__gte=start_date)
    if end_date:
        ticket_history_list = ticket_history_list.filter(created_at__lte=end_date)
        
    if search_value:
        tokens = [t.strip() for t in search_value.split(',') if t.strip()]
        if tokens:
            q_search = Q()
            for tok in tokens:
                q_tok = (
                    Q(email__icontains=tok) |
                    Q(create_by__username__icontains=tok) |
                    Q(create_by__first_name__icontains=tok) |
                    Q(create_by__last_name__icontains=tok) |
                    Q(audiofile_id__icontains=tok) |
                    Q(status__icontains=tok) |
                    Q(code__icontains=tok)
                )
                q_search &= q_tok
            ticket_history_list = ticket_history_list.filter(q_search)
        
    records_filtered = ticket_history_list.count()
    ticket_history_page = ticket_history_list[start:start + length]
    
    data = []
    for idx, ticket_history in enumerate(ticket_history_page, start=start+1):
        # make sure fields are JSON-serializable
        creator = getattr(ticket_history, 'create_by', None)
        if hasattr(creator, 'username'):
            creator_val = creator.username
        else:
            creator_val = str(creator) if creator is not None else ''

        created_at_val = getattr(ticket_history, 'create_at', None) or getattr(ticket_history, 'created_at', None)
        if isinstance(created_at_val, datetime):
            created_at_str = created_at_val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            created_at_str = str(created_at_val) if created_at_val is not None else ''

        # build readable file list from stored set-like string {"2","3"}
        file_ids_raw = getattr(ticket_history, 'audiofile_id', '') or ''
        file_names = []
        if file_ids_raw:
            try:
                json_str = file_ids_raw.replace('{', '[').replace('}', ']')
                ids = json.loads(json_str)
            except Exception:
                import re as _re
                ids = _re.findall(r"\d+", str(file_ids_raw))

            try:
                for aid in ids:
                    try:
                        a_id = int(aid)
                    except Exception:
                        a_id = aid
                    ai = AudioInfo.objects.filter(audiofile__id=a_id).select_related('audiofile').first()
                    if ai and getattr(ai, 'audiofile', None) and getattr(ai.audiofile, 'file_name', None):
                        file_names.append(ai.audiofile.file_name)
                    else:
                        file_names.append(str(aid))
            except Exception:
                file_names = [str(file_ids_raw)]

        files_audio_display = ', '.join(file_names) if file_names else ''

        data.append({
            "id": idx,
            "email": ticket_history.email,
            "code": ticket_history.code,
            "create_by": creator_val,
            "files_audio": files_audio_display,
            "start_date": ticket_history.start_at.strftime("%Y-%m-%d") if ticket_history.start_at else '',
            "exprie_date": ticket_history.expire_at.strftime("%Y-%m-%d") if ticket_history.expire_at else '',
            "status": ticket_history.status,
            "created_at": created_at_str
        })
        
    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })
            

                     