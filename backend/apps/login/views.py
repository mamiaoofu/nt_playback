import json
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth import login
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from apps.core.utils.tokens import DailyExpiryRefreshToken as RefreshToken, _get_daily_expiry
from django.middleware.csrf import get_token
from django.contrib.sessions.models import Session
from django.utils import timezone

from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# ปรับ Import ให้ตรงกับโครงสร้างไฟล์ใหม่ (apps/core/utils/function.py)
from apps.core.utils.function import create_user_log

# ปรับ Import UserProfile (คาดว่าน่าจะอยู่ที่ apps.core.models หรือ apps.users.models)
# หากยังไม่มีไฟล์ models ให้ตรวจสอบ path นี้อีกครั้ง
try:
    from apps.core.model.authorize.models import UserProfile, UserAuth, UserFileShare
except ImportError:
    # Fallback หรือ Mock กรณีหาไม่เจอเพื่อป้องกัน Server Crash
    UserProfile = None

@csrf_exempt
def index(request):
    if request.method == 'POST':
        try:
            # รับข้อมูล JSON จาก Vue Frontend
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # ใช้ AuthenticationForm ตรวจสอบความถูกต้อง (Username/Password)
        form = AuthenticationForm(request, data=data)
        
        if form.is_valid():
            user = form.get_user()
            
            try:
                if 'UserFileShare' in globals() and UserFileShare:
                    # Only consider objects of type 'ticket'
                    ticket = UserFileShare.objects.filter(user=user, type='ticket').first()
                    if ticket:
                        # expired ticket
                        if ticket.expire_at and timezone.now() > ticket.expire_at:
                            ticket.status = False
                            ticket.save()
                            user.is_active = False
                            user.save()
                            create_user_log(
                                user=user,
                                action="Login",
                                detail=f"Login failed: Ticket expired for user {user.username}",
                                status="error",
                                request=request
                            )
                            return JsonResponse({'error': 'Your ticket has expired.'}, status=401)

                        # If access_time is defined and already exhausted, deny login
                        try:
                            if ticket.access_time is not None and int(ticket.access_time) <= 0:
                                create_user_log(
                                    user=user,
                                    action="Login",
                                    detail=f"Login failed: Ticket access_time exhausted for user {user.username}",
                                    status="error",
                                    request=request
                                )
                                return JsonResponse({'error': 'Your ticket has no remaining accesses.'}, status=401)
                        except Exception:
                            # if access_time is not an int or other issue, continue without blocking
                            pass
            except Exception as e:
                print(f"Error checking ticket expiration: {e}")
            
            # Login เข้า Session (เผื่อกรณี Hybrid หรือ Admin)
            login(request, user)

            # Invalidate any other existing sessions for this user so
            # concurrent logins are prevented (other devices will be logged out).
            try:
                # ensure current session key exists
                session_key = request.session.session_key
                if not session_key:
                    request.session.save()
                    session_key = request.session.session_key

                # iterate all sessions and remove those belonging to this user
                for s in Session.objects.all():
                    try:
                        data = s.get_decoded()
                    except Exception:
                        continue
                    if str(data.get('_auth_user_id')) == str(user.id) and s.session_key != session_key:
                        s.delete()
            except Exception as e:
                print('Error clearing other sessions on login:', e)

            password_reset_required = False
            # ดึงข้อมูล Profile และตั้งค่า Session (ตาม Logic เดิม)
            if UserProfile:
                user_profile = UserProfile.objects.filter(user=user).first()
                request.session['show_toast'] = True
                if user_profile:
                    request.session['privilege_history'] = user_profile.privilege_history
                    if user_profile.reset_password == 9:
                        password_reset_required = True
                    
            print(f"User login {user.username} logged in successfully.")

            # ✅ บันทึก Log สำเร็จ
            create_user_log(
                user=user,
                action="Login",
                detail=f"Username: {user.username} login success",
                status="success",
                request=request
            )

            # If this user has a ticket with a limited access_time, decrement it
            try:
                if 'UserFileShare' in globals() and UserFileShare:
                    ticket = UserFileShare.objects.filter(user=user, type='ticket').first()
                    if ticket and ticket.access_time is not None:
                        try:
                            # decrement by 1 on successful login
                            ticket.access_time = int(ticket.access_time) - 1
                            # never allow negative values
                            if ticket.access_time < 0:
                                ticket.access_time = 0
                            ticket.save()
                        except Exception:
                            pass
            except Exception:
                pass

            # Blacklist any existing refresh tokens for this user so previous
            # JWTs cannot be used after this new login.
            try:
                for ot in OutstandingToken.objects.filter(user=user):
                    try:
                        BlacklistedToken.objects.get_or_create(token=ot)
                    except Exception:
                        # continue if already blacklisted or other issue
                        continue
            except Exception as e:
                print('Error blacklisting old tokens:', e)

            # สร้าง JWT Token ส่งกลับไปให้ Frontend
            refresh = RefreshToken.for_user(user)

            # Also generate and send CSRF token and set CSRF cookie on the response
            csrf_token = get_token(request)
            user_auth = UserAuth.objects.filter(user=user).select_related('user_permission').first()
            role = user_auth.user_permission.name
            resp = JsonResponse({
                'access': str(refresh.access_token),
                'username': user.username,
                'csrfToken': csrf_token,
                'message': 'Login successful',
                'role': role,
                'password_reset_required': password_reset_required,
            })
            try:
                secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
                samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
                # set csrf cookie as before
                resp.set_cookie(getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken'), csrf_token, secure=secure, samesite=samesite)
                # set refresh token as HttpOnly cookie so frontend JS cannot access it
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    refresh_cookie_name = getattr(settings, 'REFRESH_COOKIE_NAME', 'refresh')
                    _now = datetime.now(ZoneInfo('Asia/Bangkok'))
                    refresh_max_age = max(0, int((_get_daily_expiry() - _now).total_seconds()))
                except Exception:
                    refresh_cookie_name = 'refresh'
                    refresh_max_age = None
                try:
                    # httponly to prevent JS access; secure/samesite same as CSRF
                    resp.set_cookie(refresh_cookie_name, str(refresh), httponly=True, secure=secure, samesite=samesite, max_age=refresh_max_age)
                except Exception:
                    pass
            except Exception:
                pass
            return resp

        else:
            # ❌ Login ล้มเหลว -> บันทึก Log Error
            username_input = data.get('username', 'unknown')
            create_user_log(
                user=None,
                action="Login",
                detail=f"Failed login attempt with username: {username_input}",
                status="error",
                request=request
            )
            
            # ส่ง Error กลับเป็น JSON
            return JsonResponse({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status=401)

    # Allow GET to serve the frontend SPA (redirect to root), so visiting
    # /login/ in the browser loads the Vue app which then renders the login view.
    if request.method == 'GET':
        return redirect('/')

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_logout(request):
    """Logout endpoint: blacklist provided refresh token (if any),
    blacklist all outstanding tokens for the authenticated user as fallback,
    and remove server-side session.
    """
    try:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}') if request.body else {}
        except Exception:
            data = {}

        refresh_cookie_name = getattr(settings, 'REFRESH_COOKIE_NAME')
        session_cookie_name = getattr(settings, 'SESSION_COOKIE_NAME')
        token = data.get('refresh') or request.COOKIES.get(refresh_cookie_name)

        # prepare reporting fields
        token_blacklisted = False
        tokens_blacklisted_count = 0
        sessions_deleted_count = 0
        cookies_present = {
            'refresh': refresh_cookie_name in request.COOKIES,
            'session': session_cookie_name in request.COOKIES,
        }

        # If client provided a refresh token, blacklist it explicitly
        if token:
            try:
                RefreshToken(token).blacklist()
                token_blacklisted = True
                tokens_blacklisted_count = 1
            except Exception:
                token_blacklisted = False

        # Always blacklist all outstanding tokens for the authenticated user
        try:
            if hasattr(request, 'user') and request.user and request.user.is_authenticated:
                for ot in OutstandingToken.objects.filter(user=request.user):
                    try:
                        bt, created = BlacklistedToken.objects.get_or_create(token=ot)
                        if created:
                            tokens_blacklisted_count += 1
                    except Exception:
                        continue
                # If any tokens were blacklisted or a provided token was blacklisted
                token_blacklisted = token_blacklisted or (tokens_blacklisted_count > 0)
                # Notify user's websocket group to force client-side logout
                try:
                    user = request.user
                    if user and getattr(user, 'id', None):
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f'user_{user.id}',
                            {'type': 'force_logout', 'message': 'server_initiated_logout'}
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # Record request user/session for debugging
        try:
            req_user_authenticated = bool(getattr(request, 'user', None) and request.user.is_authenticated)
            req_user_id = getattr(request.user, 'id', None) if req_user_authenticated else None
        except Exception:
            req_user_authenticated = False
            req_user_id = None
        try:
            req_session_key = getattr(request.session, 'session_key', None)
        except Exception:
            req_session_key = None

        # log debug info
        try:
            print(f"api_logout called: user_authenticated={req_user_authenticated}, user_id={req_user_id}, session_key={req_session_key}, cookies={request.COOKIES}")
        except Exception:
            pass

        # Perform Django logout with explicit session-key deletion first
        try:
            # capture user id and session key before logout for session cleanup
            user = getattr(request, 'user', None)
            # try to delete the exact session referenced by the request (best-effort)
            try:
                if req_session_key:
                    deleted, details = Session.objects.filter(session_key=req_session_key).delete()
                    sessions_deleted_count += int(deleted or 0)
                    try:
                        print(f"Deleted session by key={req_session_key}: deleted={deleted}")
                    except Exception:
                        pass
            except Exception:
                pass

            # then perform Django logout (this will clear auth on the request)
            django_logout(request)

            # As a fallback, remove any remaining server sessions belonging to this user
            try:
                if user and getattr(user, 'id', None):
                    for s in Session.objects.all():
                        try:
                            sdata = s.get_decoded()
                        except Exception:
                            continue
                        if str(sdata.get('_auth_user_id')) == str(user.id):
                            try:
                                s.delete()
                                sessions_deleted_count += 1
                            except Exception:
                                continue
            except Exception:
                pass
        except Exception:
            pass

        # delete refresh cookie and session cookie on logout
        resp_data = {
            'detail': 'logged out',
            'token_blacklisted': token_blacklisted,
            'tokens_blacklisted_count': tokens_blacklisted_count,
            'sessions_deleted_count': sessions_deleted_count,
            'cookies_present': cookies_present,
            'cookies_delete_attempted': False,
        }
        resp = JsonResponse(resp_data)
        try:
            secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
            samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
            cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
            # Attempt deletion via delete_cookie (framework helper)
            try:
                resp.delete_cookie(refresh_cookie_name, path='/', domain=cookie_domain, samesite=samesite)
            except Exception:
                pass
            try:
                resp.delete_cookie(session_cookie_name, path='/', domain=cookie_domain, samesite=samesite)
            except Exception:
                pass
            # Also set explicit expired Set-Cookie headers as a fallback
            try:
                # refresh is HttpOnly
                resp.set_cookie(refresh_cookie_name, '', httponly=True, max_age=0, expires='Thu, 01 Jan 1970 00:00:00 GMT', path='/', domain=cookie_domain, secure=secure, samesite=samesite)
            except Exception:
                pass
            try:
                resp.set_cookie(session_cookie_name, '', httponly=True, max_age=0, expires='Thu, 01 Jan 1970 00:00:00 GMT', path='/', domain=cookie_domain, secure=secure, samesite=samesite)
            except Exception:
                pass
            # indicate we attempted cookie deletion when any cookie was present
            resp_data['cookies_delete_attempted'] = bool(cookies_present.get('refresh') or cookies_present.get('session'))
            # include debug fields about request user/session
            resp_data['request_user_authenticated'] = req_user_authenticated
            resp_data['request_user_id'] = req_user_id
            resp_data['request_session_key'] = req_session_key
            # rebuild response with updated info and set-cookie headers applied
            resp = JsonResponse(resp_data)
            try:
                resp.delete_cookie(refresh_cookie_name, path='/', domain=cookie_domain, samesite=samesite)
            except Exception:
                pass
            try:
                resp.delete_cookie(session_cookie_name, path='/', domain=cookie_domain, samesite=samesite)
            except Exception:
                pass
            try:
                resp.set_cookie(refresh_cookie_name, '', httponly=True, max_age=0, expires='Thu, 01 Jan 1970 00:00:00 GMT', path='/', domain=cookie_domain, secure=secure, samesite=samesite)
            except Exception:
                pass
            try:
                resp.set_cookie(session_cookie_name, '', httponly=True, max_age=0, expires='Thu, 01 Jan 1970 00:00:00 GMT', path='/', domain=cookie_domain, secure=secure, samesite=samesite)
            except Exception:
                pass
        except Exception:
            pass
        return resp
    except Exception:
        return JsonResponse({'detail': 'error'}, status=400)


@csrf_exempt
def api_refresh_from_cookie(request):
    """Return a new access token by reading the HttpOnly refresh cookie.
    This is a convenience endpoint for SPA clients that store the refresh
    token in an HttpOnly cookie and cannot read it from JS.
    """
    try:
        refresh_cookie_name = getattr(settings, 'REFRESH_COOKIE_NAME', 'refresh')
        token = request.COOKIES.get(refresh_cookie_name)
        if not token:
            return JsonResponse({'detail': 'no_refresh_cookie'}, status=401)
        try:
            rt = RefreshToken(token)
            access = str(rt.access_token)
            return JsonResponse({'access': access})
        except Exception:
            return JsonResponse({'detail': 'invalid_refresh'}, status=401)
    except Exception:
        return JsonResponse({'detail': 'error'}, status=400)
