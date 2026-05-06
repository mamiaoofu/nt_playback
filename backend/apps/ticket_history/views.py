from django.shortcuts import  redirect
from functools import wraps, reduce
import operator
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
import re
from django.middleware.csrf import get_token
from django.conf import settings
from apps.core.utils.function import create_user_log
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from apps.core.utils.permissions import get_user_actions, require_action
# models
from apps.core.model.authorize.models import UserAuth,MainDatabase,SetAudio,UserProfile,Agent,UserFileShare
from apps.core.model.audio.models import AudioInfo

User = get_user_model()

def ApiGetTicketHistory(request,type):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "").strip()
    create_by = request.POST.get("create_by") or request.GET.get("create_by")
    ticket_id = request.POST.get("ticket_id") or request.GET.get("ticket_id")
    
    start_date = request.POST.get("start_date") or request.GET.get("start_date")
    end_date = request.POST.get("end_date") or request.GET.get("end_date")

    
    def _parse_date_param(val, is_end=False):
        if not val:
            return None
        dt = None
        try:
            dt = timezone.datetime.fromisoformat(val) if hasattr(timezone, 'datetime') else None
        except Exception:
            dt = None

        # fallback to parse common formats
        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(val, fmt)
                    break
                except Exception:
                    dt = None

        if dt is None:
            return None

        # If date-only string, expand to start/end of day
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
            if is_end:
                dt = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
            else:
                dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0)

        if settings.USE_TZ and dt.tzinfo is None:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        return dt

    
    ticket_history_list = UserFileShare.objects.filter(type=type)
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

    # filter by create_by username (supports comma-separated usernames)
    if create_by:
        try:
            names = [n.strip() for n in str(create_by).split(',') if n and n.strip() and n.strip().lower() != 'all']
            if names:
                if len(names) > 1:
                    ticket_history_list = ticket_history_list.filter(create_by__username__in=names)
                else:
                    ticket_history_list = ticket_history_list.filter(create_by__username=names[0])
        except Exception:
            # fallback to contains
            try:
                ticket_history_list = ticket_history_list.filter(create_by__username__icontains=create_by)
            except Exception:
                pass

    # parse start/end parameters and apply filters (support only-start, only-end, or both)
    dt_start = _parse_date_param(start_date, is_end=False) if start_date else None
    dt_end = _parse_date_param(end_date, is_end=True) if end_date else None

    # date filtering now targets the ticket's create_at field
    if dt_start and dt_end:
        ticket_history_list = ticket_history_list.filter(create_at__range=(dt_start, dt_end))
    elif dt_start:
        ticket_history_list = ticket_history_list.filter(create_at__gte=dt_start)
    elif dt_end:
        ticket_history_list = ticket_history_list.filter(create_at__lte=dt_end)
        
    if search_value:
        tokens = [t.strip() for t in search_value.split(',') if t.strip()]
        if tokens:
            # prefetch audio ids that match any token in filenames (single DB query)
            try:
                # limit number of matched audio ids to avoid building huge OR queries
                audio_name_qs = [Q(audiofile__file_name__icontains=t) for t in tokens]
                combined_audio_q = reduce(operator.or_, audio_name_qs)
                matching_audio_ids_all = list(AudioInfo.objects.filter(combined_audio_q).distinct().values_list('audiofile__id', flat=True)[:100])
            except Exception:
                matching_audio_ids_all = []

            q_parts = []
            for tok in tokens:
                lower = tok.lower()
                try:
                    m_lim = re.match(r'^(?:(limit_access_time|limit_time|limit|lat|access_time|access|at))\s*(?:(>=|<=|>|<|=|:))\s*(\d+)$', tok, re.I)
                    if m_lim:
                        name = (m_lim.group(1) or '').lower()
                        op = m_lim.group(2)
                        try:
                            n = int(m_lim.group(3))
                        except Exception:
                            n = None
                        if n is not None:
                            # decide which model field the token refers to
                            if name.startswith('access') or name == 'at':
                                field = 'access_time'
                            else:
                                field = 'limit_access_time'

                            if op in (':', '='):
                                q_parts.append(Q(**{field: n}))
                            elif op == '>':
                                q_parts.append(Q(**{f"{field}__gt": n}))
                            elif op == '<':
                                q_parts.append(Q(**{f"{field}__lt": n}))
                            elif op == '>=':
                                q_parts.append(Q(**{f"{field}__gte": n}))
                            elif op == '<=':
                                q_parts.append(Q(**{f"{field}__lte": n}))
                            continue
                except Exception:
                    pass
                # skip very short tokens to avoid noise, but allow numeric tokens
                # (user ids or numeric codes) even if shorter than 3
                if len(tok.strip()) < 3 and not tok.isdigit():
                    continue

                # priority special keyword matches
                if re.match(r'^(exp|expired|expi|expir)', lower):
                    q_tok = Q(status=False)
                    q_parts.append(q_tok)
                    continue
                if re.match(r'^(act|act|active|actv)', lower):
                    q_tok = Q(status=True)
                    q_parts.append(q_tok)
                    continue
                if re.match(r'^(inc|inactive|inact)', lower):
                    q_tok = Q(status=False)
                    q_parts.append(q_tok)
                    continue

                # detect email-like token
                if '@' in tok:
                    q_tok = Q(email__icontains=tok)
                    q_parts.append(q_tok)
                    continue

                # detect file-name-like token (has extension or underscores+digits)
                file_like = False
                if re.search(r'\.[a-z0-9]{1,6}$', lower) or ('_' in tok and re.search(r'\d', tok)):
                    file_like = True

                # Attempt to find matching AudioInfo for this token regardless
                # of whether it looks 'file-like'. This ensures numeric chunks
                # inside filenames (e.g., '140220') are matched.
                try:
                    ids = list(AudioInfo.objects.filter(audiofile__file_name__icontains=tok).distinct().values_list('audiofile__id', flat=True)[:100])
                except Exception:
                    ids = []

                if ids:
                    audio_q = Q()
                    for aid in ids:
                        audio_q |= Q(audiofile_id__icontains=f'"{aid}"')
                    q_parts.append(audio_q)
                    continue

                if file_like:
                    try:
                        # search AudioInfo per-token, limited to avoid heavy queries
                        ids = list(AudioInfo.objects.filter(audiofile__file_name__icontains=tok).distinct().values_list('audiofile__id', flat=True)[:100])
                    except Exception:
                        ids = []
                    if ids:
                        audio_q = Q()
                        for aid in ids:
                            audio_q |= Q(audiofile_id__icontains=f'"{aid}"')
                        q_parts.append(audio_q)
                    else:
                        # fallback to matching raw token inside audiofile_id or code
                        q_parts.append(Q(audiofile_id__icontains=tok) | Q(code__icontains=tok))
                    continue

                # if token is numeric or a date-like string, handle accordingly
                # 1) full ISO date 'YYYY-MM-DD' -> match exact date on datetime fields
                # 2) numeric tokens:
                #    - 4-digit -> treat as year and match __year
                #    - 1-2 digit -> match day (__day) and month (__month)
                #    - always also attempt to match id/user_id exact and code contains
                parsed_date = None
                if re.match(r'^\d{4}-\d{2}-\d{2}$', tok):
                    parsed_date = datetime.strptime(tok, '%Y-%m-%d').date()
                else:
                    parsed_date = None

                if parsed_date:
                    q_parts.append(Q(start_at__date=parsed_date) |
                                   Q(expire_at__date=parsed_date) |
                                   Q(create_at__date=parsed_date) |
                                   Q(code__icontains=tok))
                    continue

                # support year-month tokens like YYYY-MM (e.g., '2026-03')
                try:
                    if re.match(r'^\d{4}-\d{2}$', tok):
                        y, m = tok.split('-')
                        y_i = int(y)
                        m_i = int(m)
                        q_tok = (
                            Q(start_at__year=y_i, start_at__month=m_i) |
                            Q(expire_at__year=y_i, expire_at__month=m_i) |
                            Q(create_at__year=y_i, create_at__month=m_i) |
                            Q(code__icontains=tok)
                        )
                        q_parts.append(q_tok)
                        continue
                except Exception:
                    pass

                if tok.isdigit():
                    try:
                        n = int(tok)
                        # build date-related Q depending on token length
                        if len(tok) == 4:
                            date_q = Q(start_at__year=n) | Q(expire_at__year=n) | Q(create_at__year=n)
                        else:
                            date_q = (
                                Q(start_at__day=n) | Q(expire_at__day=n) | Q(create_at__day=n) |
                                Q(start_at__month=n) | Q(expire_at__month=n) | Q(create_at__month=n)
                            )

                        q_tok = (
                            Q(user_id=n) |
                            Q(limit_access_time=n) |
                            Q(access_time=n) |
                            date_q |
                            Q(code__icontains=tok)
                        )
                    except Exception:
                        q_tok = Q(code__icontains=tok)
                    q_parts.append(q_tok)
                    continue

                # support tokens containing slash (e.g., "9/10" or "10/10")
                if '/' in tok:
                    try:
                        # normalize spaces around slash (allow '96 / 99')
                        tok_clean = re.sub(r"\s*/\s*", "/", tok)
                        nums = re.findall(r"\d+", tok_clean)
                        # if two numbers like '96/99', match both fields together
                        q_slash = Q()
                        if len(nums) >= 2:
                            try:
                                a = int(nums[0])
                                b = int(nums[1])
                                # If both numbers are identical (e.g., "10/10"),
                                # require both fields to match to avoid matching rows
                                # like "9/10" where only one side equals 10.
                                if a == b:
                                    q_slash = Q(limit_access_time=a, access_time=a)
                                else:
                                    q_slash = Q(limit_access_time=a, access_time=b) | Q(limit_access_time=b, access_time=a)
                            except Exception:
                                q_slash = Q()
                        else:
                            # fallback: match any numeric part against either field
                            for nstr in nums:
                                try:
                                    n = int(nstr)
                                    q_slash |= (Q(limit_access_time=n) | Q(access_time=n))
                                except Exception:
                                    pass
                        # include description match in the same OR group to avoid ANDing
                        q_slash |= Q(description__icontains=tok_clean)
                        q_parts.append(q_slash)
                        continue
                    except Exception:
                        pass

                # default: search username/name/code/email/description fields
                q_tok = (
                    Q(create_by__username__icontains=tok) |
                    Q(create_by__first_name__icontains=tok) |
                    Q(create_by__last_name__icontains=tok) |
                    Q(code__icontains=tok) |
                    Q(email__icontains=tok) |
                    Q(description__icontains=tok)
                )
                q_parts.append(q_tok)

            # combine parts with AND so all tokens must match somewhere in the row
            if q_parts:
                try:
                    combined_q = reduce(operator.and_, q_parts)
                except Exception:
                    combined_q = Q()
                    for p in q_parts:
                        combined_q &= p
                ticket_history_list = ticket_history_list.filter(combined_q)
        
    records_filtered = ticket_history_list.count()
    # Sorting support (e.g., sort[0][field]=create_at, sort[0][dir]=desc)
    sort_field = request.POST.get("sort[0][field]") or request.GET.get("sort[0][field]")
    sort_dir = (request.POST.get("sort[0][dir]") or request.GET.get("sort[0][dir]") or "asc").lower()
    if sort_field:
        field_map = {
            "email": "email",
            "code": "code",
            "create_by": "create_by__username",
            "username": "user__username",
            "files_audio": "audiofile_id",
            "download": "dowload",
            "description": "description",
            "limit_access_time": "limit_access_time",
            "create_at": "create_at",
            "start_date": "start_at",
            "expire_date": "expire_at",
            "exprie_date": "expire_at",
            "status": "status",
            "user_id": "user_id",
        }
        mapped = field_map.get(sort_field)
        try:
            if mapped:
                prefix = "-" if sort_dir == "desc" else ""
                ticket_history_list = ticket_history_list.order_by(prefix + mapped)
            elif sort_field == 'create_by_fullname':
                # special-case: sort by first_name then last_name
                if sort_dir == 'desc':
                    ticket_history_list = ticket_history_list.order_by('-create_by__first_name', '-create_by__last_name')
                else:
                    ticket_history_list = ticket_history_list.order_by('create_by__first_name', 'create_by__last_name')
        except Exception:
            pass

    ticket_history_page = ticket_history_list[start:start + length]
    
    data = []
    for idx, ticket_history in enumerate(ticket_history_page, start=start+1):
        # make sure fields are JSON-serializable
        creator = getattr(ticket_history, 'create_by', None)
        if hasattr(creator, 'username'):
            creator_val = creator.username
        else:
            creator_val = str(creator) if creator is not None else ''

        create_at_val = getattr(ticket_history, 'create_at', None) or getattr(ticket_history, 'create_at', None)
        if isinstance(create_at_val, datetime):
            if settings.USE_TZ:
                if create_at_val.tzinfo is None:
                    create_at_val = timezone.make_aware(create_at_val, timezone.get_current_timezone())
                ca = timezone.localtime(create_at_val)
            else:
                ca = create_at_val
            create_at_str = ca.strftime("%Y-%m-%d %H:%M:%S")
        else:
            create_at_str = str(create_at_val) if create_at_val is not None else ''

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

        # prepare localized date strings for JSON response
        start_date_str = ''
        expire_date_str = ''
        if getattr(ticket_history, 'start_at', None):
            sa_val = ticket_history.start_at
            if settings.USE_TZ:
                if sa_val.tzinfo is None:
                    sa_val = timezone.make_aware(sa_val, timezone.get_current_timezone())
                sa = timezone.localtime(sa_val)
            else:
                sa = sa_val
            start_date_str = sa.strftime("%Y-%m-%d %H:%M:%S")
        if getattr(ticket_history, 'expire_at', None):
            ea_val = ticket_history.expire_at
            if settings.USE_TZ:
                if ea_val.tzinfo is None:
                    ea_val = timezone.make_aware(ea_val, timezone.get_current_timezone())
                ea = timezone.localtime(ea_val)
            else:
                ea = ea_val
            expire_date_str = ea.strftime("%Y-%m-%d %H:%M:%S")

        data.append({
            "id": ticket_history.id,
            "email": ticket_history.email,
            "code": ticket_history.code,
            "create_by": creator_val,
            "files_audio": files_audio_display,
            "start_date": start_date_str,
            "exprie_date": expire_date_str,
            "limit_access_time": getattr(ticket_history, 'limit_access_time', None),
            "access_time": getattr(ticket_history, 'access_time', None),
            "status": ticket_history.status,
            "create_at": create_at_str,
            "user_id" : ticket_history.user_id,
            'username': ticket_history.user.username,
            'description': ticket_history.description,
            'dowload': ticket_history.dowload,
        })
        
    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })

@login_required
@require_action('Change Delegate File Status', 'Change Ticket Status')
@require_POST    
def ApiChangeFileShareStatus(request, user_id, type):
    try:
        user = User.objects.get(id=user_id)
        
        user_file_id = request.POST.get('user_file_id')
        user_file_share = UserFileShare.objects.get(id=user_file_id)
        
        if type == "ticket":
            user.is_active = not user.is_active
            user.save()
            user_file_share.status = not user_file_share.status
            user_file_share.save()
            status_msg = 'Active' if user.is_active else 'Inactive'
        elif type == "delegate":
            user_file_share.status = not user_file_share.status
            user_file_share.save()
            status_msg = 'Active' if user_file_share.status else 'Inactive' 
        
        
        create_user_log(user=request.user, action="Change User Status", detail=f"Changed status of {user_file_share.code} to {status_msg}", status="success", request=request)
        return JsonResponse({'status': 'success', 'message': f'{type} ID {user_file_share.code} is now {status_msg}.'})
    except User.DoesNotExist:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : User not found", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': 'User not found.'})
    except Exception as e:
        create_user_log(user=request.user, action="Change User Status", detail=f"message : {str(e)}", status="error", request=request)
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def ApiGenFormTicket(request):
    try:
        user_file_id = request.POST.get('user_file_id') or request.GET.get('user_file_id')
        user_id = request.POST.get('user_id') or request.GET.get('user_id')
        if not user_file_id or not user_id:
            return JsonResponse({'status': 'error', 'message': 'Missing parameters'})

        user_file_share = UserFileShare.objects.get(id=user_file_id)
        user = User.objects.get(id=user_id)

        # Cannot reverse an MD5 hash to plain text. Instead generate a new
        # temporary password (6 chars from the requested charset), set it on
        # the user (using Django's set_password) and return the plain
        # temporary password to the frontend.
        allowed = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
        temp_pw = get_random_string(6, allowed)
        user.set_password(temp_pw)
        user.save()

        result = {
            'email': user_file_share.email,
            'code': user_file_share.code,
            'password': temp_pw,
            'start_at': user_file_share.start_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(user_file_share, 'start_at', None) else '',
            'expire_at': user_file_share.expire_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(user_file_share, 'expire_at', None) else ''
        }
        create_user_log(user=request.user, action="Gen Ticket", detail=f"Generated ticket {user_file_share.code} for user {user.username}", status="success", request=request)
        return JsonResponse(result)
    except UserFileShare.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'UserFileShare not found'})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

                     