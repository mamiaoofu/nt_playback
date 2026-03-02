from django.shortcuts import  redirect
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import re
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives

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
from django.contrib.auth.models import User
from django.db import transaction
from .models import FavoriteSearch, SetColumnAudioRecord, ConfigKey
from .serializers import FavoriteSearchSerializer
from apps.configuration.models import UserPermission

#serializer
from apps.core.model.authorize.serializers import MainDatabaseSerializer

one_year_ago = timezone.now() - timedelta(days=365)

server_ip = socket.gethostbyname(socket.gethostname())

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
def ApiGetCsrfToken(request):
    token = get_token(request)
    resp = JsonResponse({'csrfToken': token})
    try:
        # Ensure the CSRF cookie is explicitly set on the response so client can read/send it.
        # Use project settings fallbacks for secure and samesite behavior.
        secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
        # Django's default CSRF cookie name is settings.CSRF_COOKIE_NAME
        resp.set_cookie(getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken'), token, secure=secure, samesite=samesite)
    except Exception:
        pass
    return resp


@login_required(login_url='/login')
@require_POST
def ApiSendShareEmail(request):
    try:
        body = request.body.decode('utf-8') or '{}'
        data = json.loads(body)
        recipient = data.get('recipient')
        subject = data.get('subject', 'Files shared with you')
        text_message = data.get('body', '')
        html_message = data.get('html')
        if not recipient:
            return JsonResponse({'ok': False, 'error': 'recipient required'}, status=400)

        # Normalize recipient(s) to a list of email strings
        recipients = []
        if isinstance(recipient, (list, tuple)):
            recipients = [r for r in recipient if r]
        elif isinstance(recipient, str):
            # allow comma/semicolon/newline separated lists
            parts = [p.strip() for p in re.split('[,;\n\r]+', recipient) if p.strip()]
            recipients = parts
        else:
            return JsonResponse({'ok': False, 'error': 'invalid recipient format'}, status=400)

        if not recipients:
            return JsonResponse({'ok': False, 'error': 'no recipients found'}, status=400)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))

        # send emails in parallel to reduce total latency
        from concurrent.futures import ThreadPoolExecutor, as_completed

        errors = []

        def _send_single(to_addr):
            try:
                if html_message:
                    msg = EmailMultiAlternatives(subject, text_message or '', from_email, [to_addr])
                    msg.attach_alternative(html_message, 'text/html')
                    msg.send(fail_silently=False)
                else:
                    send_mail(subject, text_message, from_email, [to_addr], fail_silently=False)
                return True, None
            except Exception as e:
                return False, str(e)

        max_workers = min(10, len(recipients))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_send_single, r): r for r in recipients}
            for fut in as_completed(futures):
                ok, err = fut.result()
                if not ok:
                    errors.append({'recipient': futures[fut], 'error': err})

        if errors:
            return JsonResponse({'ok': False, 'errors': errors}, status=500)

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@login_required(login_url='/login')
@require_action('Audio Recording','User Logs')
def ApiIndexHome(request):
    show_toast = request.session.get('show_toast', False)
    if show_toast:
        del request.session['show_toast']

    set_audio = SetAudio.objects.filter(user=request.user).first()
    user_auth_qs = UserAuth.objects.filter(user=request.user, allow=True)
    # get MainDatabase objects allowed for this user
    main_db_ids = list(user_auth_qs.values_list('maindatabase_id', flat=True))
    main_db = MainDatabase.objects.filter(id__in=main_db_ids).order_by('database_name')
    user_profile = UserProfile.objects.filter(user=request.user).first()
    favorite_search = FavoriteSearch.objects.filter(user=request.user).first()
    favorite_search_all = FavoriteSearch.objects.filter(user=request.user).all()
    audio_column = SetColumnAudioRecord.objects.filter(user=request.user).first()
    agent = Agent.objects.all()
    raw_data = favorite_search.raw_data if favorite_search else {}

    main_db_serialized = MainDatabaseSerializer(main_db, many=True).data
    favorite_search_all_serialized = FavoriteSearchSerializer(favorite_search_all, many=True).data
    favorite_search_serialized = FavoriteSearchSerializer(favorite_search).data if favorite_search else None

    return JsonResponse({
        'show_toast': show_toast,
        'main_db': main_db_serialized,
        'set_audio': set_audio.audio_path if set_audio else None,
        'user_profile': {'id': user_profile.user.id, 'username': user_profile.user.username} if user_profile else None,
        'favorite_search': favorite_search_serialized,
        'raw_data': raw_data,
        'favorite_search_all': favorite_search_all_serialized,
        'audio_column': audio_column.raw_data if audio_column else 0,
        'agent': list(agent.values('id', 'agent_code', 'first_name', 'last_name')),
    })
    
@login_required(login_url='/login')
@require_action('Playback Audio')
def ApiGetAudioList(request):
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    # sanitize pagination params
    try:
        start = max(0, int(start))
    except Exception:
        start = 0
    try:
        length = max(1, min(1000, int(length)))
    except Exception:
        length = 25

    search_value = (request.GET.get("search[value]", "") or "").strip()

    set_audio = SetAudio.objects.filter(user=request.user).first()
    main_db_id = UserAuth.objects.filter(user=request.user, allow=True).values_list("maindatabase_id", flat=True)

    # Check for file_share parameter or ticket user
    is_ticket = UserFileShare.objects.filter(user=request.user, type='ticket').exists()
    
    if is_ticket :
        audio_list = AudioInfo.objects.filter()
    else :
        audio_list = AudioInfo.objects.select_related("audiofile", "agent", "customer").filter(main_db__in=main_db_id)

    # ฟิลเตอร์จาก request.form หรือ request.GET
    database_name = request.POST.get("database_name") or request.GET.get("database_name")  
    start_date = request.POST.get("start_date") or request.GET.get("start_date") 
    end_date = request.POST.get("end_date") or request.GET.get("end_date")
    file_name = request.POST.get("file_name") or request.GET.get("file_name")
    duration = request.POST.get("duration") or request.GET.get("duration")
    customer = request.POST.get("customer") or request.GET.get("customer") 
    customer_number = request.POST.get("customer_number") or request.GET.get("customer_number")
    agent_id = request.POST.get("agent_id") or request.GET.get("agent_id")
    agent_group = request.POST.get("agent_group") or request.GET.get("agent_group")
    time_type = request.POST.get("type") or request.GET.get("type")
    
    call_direction = request.POST.get("call_direction") or request.GET.get("call_direction")
    extension = request.POST.get("extension") or request.GET.get("extension")
    agent_name = request.POST.get("agent") or request.GET.get("agent")
    full_name = request.POST.get("full_name") or request.GET.get("full_name")
    custom_field = request.POST.get("custom_field") or request.GET.get("custom_field")
    


    if is_ticket or (request.POST.get("file_share") == 'true' or request.GET.get("file_share") == 'true'):
        try:
            valid_shares = UserFileShare.objects.filter(user=request.user, expire_at__gte=timezone.now())
            shared_ids = []
            
            for share in valid_shares:
                if share.audiofile_id:
                    try:
                        # Convert {"1","2"} to ["1","2"] for json.loads
                        json_str = share.audiofile_id.replace('{', '[').replace('}', ']')
                        ids = json.loads(json_str)
                        shared_ids.extend(ids)
                    except Exception:
                        continue
            
            if shared_ids:
                print("shared_ids:", shared_ids)
                audio_list = audio_list.filter(audiofile__id__in=shared_ids)
            else:
                audio_list = audio_list.none()
                
            print("audio_list:", audio_list.query)    
        except Exception:
            audio_list = audio_list.none()
    
    now = datetime.now()
    if time_type:
        if time_type == "hour":
            start_date = now - timedelta(hours=1)
        elif time_type == "day":
            start_date = now - timedelta(days=1)
        elif time_type == "month":
            start_date = now - timedelta(days=30)
        elif time_type == "year":
            start_date = now - timedelta(days=365)
        start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_date = now.strftime("%Y-%m-%d %H:%M:%S")
        

    if database_name and database_name != "all":
        parts = [p.strip() for p in str(database_name).split(',') if p.strip()]
        if parts:
            ids = []
            names = []
            for p in parts:
                try:
                    ids.append(int(p))
                except Exception:
                    names.append(p)
            if ids:
                audio_list = audio_list.filter(main_db__id__in=ids)
            elif names:
                qn = Q()
                for n in names:
                    qn |= Q(main_db__database_name__icontains=n)
                audio_list = audio_list.filter(qn)

    if search_value:
        parts = search_value.split(",")
        q_global = None
        for part in parts:
            part = part.strip()
            if part:
                q_search = (
                    Q(call_direction__icontains=part) |
                    Q(extension__icontains=part) |
                    Q(agent__first_name__icontains=part) |
                    Q(agent__last_name__icontains=part) |
                    Q(customer_number__icontains=part) |
                    Q(agent__agent_code__icontains=part)
                )
                name_parts = part.split(" ", 1)
                if len(name_parts) == 2:
                    first, last = name_parts
                    q_search |= (Q(agent__first_name__icontains=first) & Q(agent__last_name__icontains=last))
                
                if q_global is None:
                    q_global = q_search
                else:
                    q_global &= q_search
        
        if q_global:
            audio_list = audio_list.filter(q_global)
            
    # Mapping simple filters (duration handled separately below)
    filter_map = {
        "start_datetime__gte": start_date,
        "start_datetime__lte": end_date,
        "audiofile__file_name__icontains": file_name,
    }

    for field, value in filter_map.items():
        if value:
            audio_list = audio_list.filter(**{field: value})

    # Handle duration filter: accept 'HH:MM:SS', 'MM:SS', 'SS' or range 'HH:MM:SS - HH:MM:SS'
    if duration:
        def parse_duration_to_timedelta(s):
            s = s.strip()
            if not s:
                return None
            parts = [p for p in s.split(":") if p != ""]
            try:
                parts = [int(p) for p in parts]
            except Exception:
                return None
            if len(parts) == 3:
                h, m, sec = parts
            elif len(parts) == 2:
                h = 0
                m, sec = parts
            elif len(parts) == 1:
                h = 0
                m = 0
                sec = parts[0]
            else:
                return None
            try:
                return timedelta(hours=h, minutes=m, seconds=sec)
            except Exception:
                return None

        dur_str = duration.strip()
        # check for range separator '-' (allow spaces around)
        if "-" in dur_str:
            parts = [p.strip() for p in dur_str.split("-") if p.strip()]
            if len(parts) == 2:
                start_td = parse_duration_to_timedelta(parts[0])
                end_td = parse_duration_to_timedelta(parts[1])
                if start_td is not None and end_td is not None:
                    # ensure start <= end
                    if start_td > end_td:
                        start_td, end_td = end_td, start_td
                    audio_list = audio_list.filter(audiofile__duration__gte=start_td, audiofile__duration__lte=end_td)
                else:
                    # fallback to best-effort string match
                    try:
                        audio_list = audio_list.filter(audiofile__duration__icontains=duration)
                    except Exception:
                        pass
            else:
                try:
                    audio_list = audio_list.filter(audiofile__duration__icontains=duration)
                except Exception:
                    pass
        else:
            # single duration value - keep previous behavior (upper bound)
            td = parse_duration_to_timedelta(dur_str)
            if td is not None:
                audio_list = audio_list.filter(audiofile__duration__lte=td)
            else:
                try:
                    audio_list = audio_list.filter(audiofile__duration__icontains=duration)
                except Exception:
                    pass

    if customer:
        parts = [p.strip() for p in customer.split(',') if p.strip()]
        if parts:
            q = Q()
            for p in parts:
                q |= Q(customer_number__icontains=p)
            audio_list = audio_list.filter(q)

    # Support payloads that send `customer_number` explicitly
    if customer_number:
        parts = [p.strip() for p in customer_number.split(',') if p.strip()]
        if parts:
            q = Q()
            for p in parts:
                q |= Q(customer_number__icontains=p)
            audio_list = audio_list.filter(q)
            
    if custom_field:
        parts = [p.strip() for p in custom_field.split(',') if p.strip()]
        if parts:
            q = Q()
            for p in parts:
                q |= Q(custom_field_1__icontains=p)
            audio_list = audio_list.filter(q)        

    if extension:
        parts = [p.strip() for p in extension.split(',') if p.strip()]
        if parts:
            q = Q()
            for p in parts:
                q |= Q(extension__icontains=p)
            audio_list = audio_list.filter(q)

    if agent_id:
        parts = [p.strip() for p in str(agent_id).split(',') if p.strip()]
        if parts:
            ids = []
            codes = []
            for p in parts:
                try:
                    ids.append(int(p))
                except Exception:
                    codes.append(p)
            if ids:
                audio_list = audio_list.filter(agent__id__in=ids)
            if codes:
                q = Q()
                for c in codes:
                    q |= Q(agent__agent_code__icontains=c)
                audio_list = audio_list.filter(q)

    if agent_group:
        groups = [g.strip() for g in agent_group.split(',') if g.strip()]
        if groups:
            audio_list = audio_list.filter(agent__agent_group_id__in=groups)

    if call_direction and call_direction != "all":
        parts = [p.strip() for p in call_direction.split(',') if p.strip()]
        if parts:
            q = Q()
            for p in parts:
                q |= Q(call_direction__icontains=p)
            audio_list = audio_list.filter(q)

    if agent_name:
        parts = agent_name.split(',')
        q_agent = Q()
        for part in parts:
            part = part.strip()
            if not part: continue
            
            if " - " in part:
                code_part, name_part = part.split(" - ", 1)
                code_part = code_part.strip()
                name_part = name_part.strip()
                
                q_sub = Q(agent__agent_code__icontains=code_part)
                if name_part:
                    name_parts = name_part.split(" ", 1)
                    if len(name_parts) == 2:
                        first, last = name_parts
                        q_sub &= (Q(agent__first_name__icontains=first) & Q(agent__last_name__icontains=last))
                    else:
                        q_sub &= (Q(agent__first_name__icontains=name_part) | Q(agent__last_name__icontains=name_part))
                q_agent |= q_sub
            else:
                name_parts = part.split(" ", 1)
                if len(name_parts) == 2:
                    first, last = name_parts
                    q_agent |= ((Q(agent__first_name__icontains=first) & Q(agent__last_name__icontains=last)) | Q(agent__agent_code__icontains=part))
                else:
                    q_agent |= (Q(agent__first_name__icontains=part) | Q(agent__last_name__icontains=part) | Q(agent__agent_code__icontains=part))
        if q_agent:
            audio_list = audio_list.filter(q_agent)

    if full_name:
        parts = full_name.split(',')
        q_full = Q()
        for part in parts:
            part = part.strip()
            if not part: continue
            name_parts = part.split(" ", 1)
            if len(name_parts) == 2:
                first, last = name_parts
                q_full |= (Q(agent__first_name__icontains=first) & Q(agent__last_name__icontains=last))
            else:
                q_full |= (Q(agent__first_name__icontains=part) | Q(agent__last_name__icontains=part))
        if q_full:
            audio_list = audio_list.filter(q_full)

    # Sorting Logic
    sort_field = request.GET.get('sort[0][field]')
    sort_dir = request.GET.get('sort[0][dir]')

    if sort_field and sort_dir:
        sort_mapping = {
            'main_db': 'main_db__database_name',
            'start_datetime': 'start_datetime',
            'end_datetime': 'end_datetime',
            'duration': 'audiofile__duration',
            'file_name': 'audiofile__file_name',
            'call_direction': 'call_direction',
            'customer_number': 'customer_number',
            'extension': 'extension',
            'agent': 'agent__agent_code',
            'full_name': ['agent__first_name', 'agent__last_name'],
            'custom_field_1': 'custom_field_1'
        }
        
        if sort_field in sort_mapping:
            fields = sort_mapping[sort_field]
            if not isinstance(fields, list):
                fields = [fields]
            
            ordering = []
            for f in fields:
                ordering.append(f'-{f}' if sort_dir == 'desc' else f)
            audio_list = audio_list.order_by(*ordering)
    else:
        audio_list = audio_list.order_by('-start_datetime')


    # count after applying filters
    records_total = audio_list.count()

    # Pagination (slice)
    audio_page = audio_list[start:start + length]

    data = []
    for idx, audio in enumerate(audio_page, start=start+1):
        main_db_display = str(audio.main_db) if hasattr(audio, 'main_db') else ''
        start_dt = audio.start_datetime.strftime("%Y-%m-%d %H:%M") if getattr(audio, 'start_datetime', None) else "-"
        end_dt = audio.end_datetime.strftime("%Y-%m-%d %H:%M") if getattr(audio, 'end_datetime', None) else "-"
        file_name = audio.audiofile.file_name if getattr(audio, 'audiofile', None) else "-"
        duration_val = str(audio.audiofile.duration) if (getattr(audio, 'audiofile', None) and getattr(audio.audiofile, 'duration', None)) else "-"
        agent_display = str(audio.agent) if getattr(audio, 'agent', None) else "-"
        full_name = f"{audio.agent.first_name} {audio.agent.last_name}" if getattr(audio, 'agent', None) else "-"

        data.append({
            "no": idx,
            "main_db": main_db_display,
            "start_datetime": start_dt,
            "end_datetime": end_dt,
            "file_name": file_name,
            "duration": duration_val,
            "call_direction": audio.call_direction,
            "customer_number": audio.customer_number,
            "extension": audio.extension,
            "agent": agent_display,
            "full_name": full_name,
            "file_path": audio.audiofile.file_path if getattr(audio, 'audiofile', None) else None,
            "file_id": audio.audiofile.id if getattr(audio, 'audiofile', None) else None,
            "set_audio": set_audio.audio_path if set_audio else None,
            "custom_field_1": custom_field
        })
        


    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_total,
        "data": data
    })

@login_required(login_url='/login')
def ApiGetMyPermissions(request):
    try:
        perms = list(get_user_actions(request.user))
        return JsonResponse({'status': 'success', 'permissions': perms})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/login')
@require_action('My Favorite Search')
def ApiSaveMyFavoriteSearch(request):
    
    if request.method == "POST":
        action = request.POST.get("action")
        user = request.user
        
        # Handle Delete
        if action == "delete":
            favorite_id = request.POST.get("favorite_id")
            try:
                fav = FavoriteSearch.objects.get(id=favorite_id, user=user)
                fav_name = fav.favorite_name
                fav.delete()
                create_user_log(user=request.user, action="Delete Favorite", detail=f"Deleted favorite: {fav_name}", status="success", request=request)
                return JsonResponse({"status": "success", "message": "Deleted successfully", "id": favorite_id})
            except Exception as e:
                create_user_log(user=request.user, action="Delete Favorite", detail=f"Error deleting favorite: {str(e)}", status="error", request=request)
                return JsonResponse({"status": "error", "message": str(e)})

        # Handle Create and Edit
        favorite_name = request.POST.get("favorite_name", "").strip()
        description = request.POST.get("favorite_description") or request.POST.get("create_favorite_description", "")
        full_name = request.POST.get("full_name") or request.POST.get("fav_fullname", "")

        
        # Collect raw data from form fields
        raw_data = {
            "database_name": request.POST.get("database_name", ""),
            "call_direction": request.POST.get("call_direction", ""),
            "start_date": request.POST.get("start_date", ""),
            "end_date": request.POST.get("end_date", ""),
            "file_name": request.POST.get("file_name", ""),
            "customer": request.POST.get("customer", ""),
            "extension": request.POST.get("extension", ""),
            "agent": request.POST.get("agent", ""),
            "full_name": full_name,
            "duration": request.POST.get("duration", ""),
        }

        if action == "create":
            if FavoriteSearch.objects.filter(user=user, favorite_name__iexact=favorite_name).exists():
                create_user_log(user=request.user, action="Create Favorite", detail=f"Duplicate name: {favorite_name}", status="error", request=request)
                return JsonResponse({"status": "error", "message": "This name is already in the system."})

            try:
                fav = FavoriteSearch.objects.create(
                    user=user,
                    favorite_name=favorite_name,
                    raw_data=raw_data,
                    description=description
                )
                create_user_log(user=request.user, action="Create Favorite", detail=f"Created favorite: {favorite_name}", status="success", request=request)
                return JsonResponse({
                    "status": "success", 
                    "message": "Created successfully",
                    "favorite": {
                        "id": fav.id,
                        "favorite_name": fav.favorite_name,
                        "raw_data": fav.raw_data,
                        "description": fav.description
                    }
                })
            except Exception as e:
                create_user_log(user=request.user, action="Create Favorite", detail=f"Error creating favorite: {str(e)}", status="error", request=request)
                return JsonResponse({"status": "error", "message": str(e)})

        elif action == "edit":
            favorite_id = request.POST.get("favorite_id")
            
            if FavoriteSearch.objects.filter(user=user, favorite_name__iexact=favorite_name).exclude(id=favorite_id).exists():
                create_user_log(user=request.user, action="Edit Favorite", detail=f"Duplicate name: {favorite_name}", status="error", request=request)
                return JsonResponse({"status": "error", "message": "This name is already in the system."})

            try:
                fav = FavoriteSearch.objects.get(id=favorite_id, user=user)
                fav.favorite_name = favorite_name
                fav.raw_data = raw_data
                fav.description = description
                fav.save()
                create_user_log(user=request.user, action="Edit Favorite", detail=f"Updated favorite: {favorite_name}", status="success", request=request)
                return JsonResponse({
                    "status": "success", 
                    "message": "Updated successfully",
                    "favorite": {
                        "id": fav.id,
                        "favorite_name": fav.favorite_name,
                        "raw_data": fav.raw_data,
                        "description": fav.description
                    }
                })
            except FavoriteSearch.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Favorite not found"})
            except Exception as e:
                create_user_log(user=request.user, action="Edit Favorite", detail=f"Error updating favorite: {str(e)}", status="error", request=request)
                return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

@login_required(login_url='/login')
@require_action('My Favorite Search')
def ApiCheckMyFavoriteName(request):
    favorite_name = request.GET.get('favoriteName', '').strip()
    favorite_id = request.GET.get('favoriteId', None)
    
    if not favorite_name:
        return JsonResponse({'status': 'success', 'is_taken': False})

    query = FavoriteSearch.objects.filter(user=request.user, favorite_name__iexact=favorite_name)
    if favorite_id:
        query = query.exclude(id=favorite_id)

    if query.exists():
        return JsonResponse({'status': 'success', 'is_taken': True, 'message': 'This name is already in the system.'})
    else:
        return JsonResponse({'status': 'success', 'is_taken': False})
    
# --- Encryption Helper (Simple XOR + Base64) ---
SECRET_KEY = b"9Xv2M4p7Q8r1Z3w5Y6t8B0n2V4c6X8m0L2k4J6h8F0d2S4a" # (ต้องตรงกับ Wrapper exe)

def encrypt_credential(text):
    if not text: return ""
    data = text.encode('utf-8')
    encrypted = bytes(a ^ b for a, b in zip(data, SECRET_KEY * (len(data) // len(SECRET_KEY) + 1)))
    return base64.b64encode(encrypted).decode('utf-8')
    
@login_required
def ApiGetCredentials(request):
    """
    API endpoint ที่ส่งข้อมูล username/password สำหรับเชื่อมต่อ network share
    โดยดึงข้อมูลจากโมเดล ConfigKey
    """
    try:
        # ดึงข้อมูลโดยใช้ 'type' เพื่อระบุว่าเป็น username หรือ password
        config_key = ConfigKey.objects.get(type='player_connect')
        credentials = {
            "username": encrypt_credential(config_key.key_username),
            "password": encrypt_credential(config_key.key_password)
        }
        return JsonResponse(credentials)
    except ConfigKey.DoesNotExist:
        create_user_log(user=request.user, action="Credentials", detail={"error": "Credentials not configured. Please create 'niceplayer_username' and 'niceplayer_password' types in ConfigKey."}, status="error", request=request)
        return JsonResponse({"error": "Credentials not configured. Please create 'niceplayer_username' and 'niceplayer_password' types in ConfigKey."}, status=500)
    except Exception as e:
        create_user_log(user=request.user, action="Credentials",  detail={"error": str(e)}, status="error", request=request)
        return JsonResponse({"error": str(e)}, status=500)
    
@login_required
@require_POST
@require_action("Playback Audio")
def ApiLogPlayAudio(request):
    """
    API endpoint สำหรับรับ Log การเล่นไฟล์เสียงจาก Frontend
    """
    try:
        data = json.loads(request.body)
        create_user_log(user=request.user, action="Playback Audio", detail=data.get('detail', ''), status=data.get('status', ''), request=request)

        return JsonResponse({"message": "Log received"}, status=201)
    except Exception as e:
        create_user_log(user=request.user, action="Playback Audio", detail={"error": str(e)}, status="error", request=request)
        
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@require_POST
@require_action('Save file')
def ApiLogSaveFile(request):
    try:
        data = json.loads(request.body)
        detail = data.get('detail', '')
        create_user_log(user=request.user, action="Save file", detail=detail, status="success", request=request)
        return JsonResponse({"status": "ok"})
    except Exception as e:
        try:
            create_user_log(user=request.user, action="Save file", detail={"error": str(e)}, status="error", request=request)
        except Exception:
            # swallow secondary errors when logging fails
            pass
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    
@login_required
@require_POST
def ApiCreateFileShare(request):
    try:
        body = request.body.decode('utf-8') or '{}'
        data = json.loads(body)

        files = data.get('files', [])
        target_type = data.get('targetType') or data.get('type')
        target = data.get('target')
        start_raw = data.get('start')
        expire_raw = data.get('expire')
        download = data.get('download', False)

        if not target_type or not target:
            return JsonResponse({'ok': False, 'message': 'Incomplete information (targetType/target)'}, status=400)

        def parse_dt(s):
            if not s:
                return None
            try:
                dt = datetime.strptime(s, '%Y-%m-%d %H:%M')
            except Exception:
                try:
                    dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    try:
                        dt = datetime.fromisoformat(s)
                    except Exception:
                        return None
            try:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
            except Exception:
                pass
            return dt

        start_dt = parse_dt(start_raw)
        expire_dt = parse_dt(expire_raw)

        audio_ids = []
        for f in files:
            try:
                fid = f.get('file_id') if isinstance(f, dict) else f
                audio_ids.append(int(fid))
            except Exception:
                continue

        audio_ids_str = "{" + ",".join([f'"{aid}"' for aid in audio_ids]) + "}"

        if target_type == 'user':
            # Accept single username or list of usernames (or delimited string)
            targets = []
            if isinstance(target, (list, tuple)):
                targets = [t for t in target if t]
            elif isinstance(target, str):
                # try parse JSON list first
                try:
                    parsed = json.loads(target)
                    if isinstance(parsed, list):
                        targets = [str(t) for t in parsed if t]
                    else:
                        targets = [target]
                except Exception:
                    targets = [t.strip() for t in re.split('[,;\n\r]+', target) if t.strip()]
            else:
                return JsonResponse({'ok': False, 'message': 'Invalid target format'}, status=400)

            if not targets:
                return JsonResponse({'ok': False, 'message': 'No target specified'}, status=400)

            missing = []
            created_count = 0
            with transaction.atomic():
                for uname in targets:
                    auth_user = User.objects.filter(username=uname).first()
                    if not auth_user:
                        missing.append(uname)
                        continue

                    UserFileShare.objects.create(
                        user=auth_user,
                        type='user',
                        code='',
                        audiofile_id=audio_ids_str,
                        start_at=start_dt or timezone.now(),
                        expire_at=expire_dt or (timezone.now() + timedelta(days=1)),
                        status=1,
                        dowload=bool(download),
                        create_by=request.user
                    )
                    created_count += 1

            create_user_log(user=request.user, action="Create File Share", detail=f"Create File Share successfully: {targets} | Type={target_type} | start={start_raw} | exp={expire_raw}", status="success", request=request)

            if missing:
                return JsonResponse({'ok': True, 'message': f'Created {created_count} shares; missing users: {missing}'} )

            return JsonResponse({'ok': True, 'message': 'The file has been successfully shared with the users.'})

        if target_type == 'ticket':
            ticket_code = data.get('ticketCode') or data.get('code')
            password = data.get('password')
            if not ticket_code or not password:
                return JsonResponse({'ok': False, 'message': 'Ticket information is incomplete. (ticketCode/password)'}, status=400)

            with transaction.atomic():
                # normalize target which may contain multiple emails
                recipients = []
                if isinstance(target, str) and target.strip():
                    recipients = [p.strip() for p in re.split('[,;\n\r]+', target) if p.strip()]

                # build Postgres-style set string: {"a","b"}
                if recipients:
                    email_set = "{" + ",".join([f'"{r}"' for r in recipients]) + "}"
                    primary_email = recipients[0]
                else:
                    email_set = target or ''
                    primary_email = target or ''

                new_user = User.objects.create(
                    username=ticket_code,
                    first_name=ticket_code,
                    last_name=ticket_code,
                    email=primary_email,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                )
                new_user.set_password(password)
                new_user.save()

                main_dbs = list(MainDatabase.objects.only('id').order_by('id'))
                user_auths = []
                permission = UserPermission.objects.get(id=4)
                for db in main_dbs:
                    user_auths.append(UserAuth(
                        user=new_user,
                        maindatabase=db,
                        allow=False,
                        user_permission=permission
                    ))
                if user_auths:
                    UserAuth.objects.bulk_create(user_auths)

                UserFileShare.objects.create(
                    user=new_user,
                    type='ticket',
                    email=email_set,
                    code=ticket_code,
                    audiofile_id=audio_ids_str,
                    start_at=start_dt or timezone.now(),
                    expire_at=expire_dt or (timezone.now() + timedelta(days=1)),
                    status=True,
                    dowload=bool(download),
                    create_by=request.user
                )

            create_user_log(user=request.user, action="Create File Share", detail=f"Create File Share successfully: {target} | Type={target_type} | start={start_raw} | exp={expire_raw}", status="success", request=request)

            return JsonResponse({'ok': True, 'message': 'Ticket created and file shared successfully.', 'ticketCode': ticket_code, 'password': password})

        create_user_log(user=request.user, action="Create File Share", detail=f"Failed to create file share: Invalid targetType {target_type}", status="error", request=request)
        return JsonResponse({'ok': False, 'message': 'targetType incorrect'}, status=400)
    except Exception as e:
        create_user_log(user=request.user, action="Create File Share", detail=f"Error creating file share: {str(e)}", status="error", request=request)
        return JsonResponse({'ok': False, 'message': f'error: {str(e)}'}, status=500)
    