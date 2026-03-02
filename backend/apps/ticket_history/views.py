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

def ApiGetTicketHistory(request, type):
    pass
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "").strip()
    
    full_name = request.POST.get("full_name") or request.GET.get("full_name")
    created_by = request.POST.get("created_by") or request.GET.get("created_by")
    
    start_date = request.POST.get("start_date") or request.GET.get("start_date")
    end_date = request.POST.get("end_date") or request.GET.get("end_date")
    files_audio = request.POST.get("files_audio") or request.GET.get("files_audio")
    status = request.POST.get("status") or request.GET.get("status")
    
    
    ticket_history_list = UserFileShare.objects.filter(type=type)
    records_total = ticket_history_list.count()
    
    if start_date:
        ticket_history_list = ticket_history_list.filter(created_at__gte=start_date)
    if end_date:
        ticket_history_list = ticket_history_list.filter(created_at__lte=end_date)
        
    if search_value:
        tokens = [t.strip() for t in search_value.split(',') if t.strip()]
        if tokens:
            q_search = Q()
            for tok in tokens:
                q_tok = (Q(full_name__icontains=tok) |
                        Q(created_by__icontains=tok) |
                        Q(files_audio__icontains=tok) |
                        Q(status__icontains=tok)) 
                q_search &= q_tok
            ticket_history_list = ticket_history_list.filter(q_search)
        
    records_filtered = ticket_history_list.count()
    ticket_history_page = ticket_history_list[start:start + length]
    
    data = []
    for idx, ticket_history in enumerate(ticket_history_page, start=start+1):
        data.append({
            "id": idx,
            "full_name": ticket_history.full_name,
            "created_by": ticket_history.created_by,
            "files_audio": ticket_history.files_audio,
            "status": ticket_history.status,
            "created_at": ticket_history.created_at
        })
        
    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })
            

                     