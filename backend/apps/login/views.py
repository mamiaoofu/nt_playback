import json
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.middleware.csrf import get_token
from django.contrib.sessions.models import Session
from django.utils import timezone

from django.conf import settings

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
                    ticket = UserFileShare.objects.filter(user=user).first()
                    if ticket and ticket.expire_at and timezone.now() > ticket.expire_at and ticket.type == 'ticket':
                        ticket.status = 'f'
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

            # ดึงข้อมูล Profile และตั้งค่า Session (ตาม Logic เดิม)
            if UserProfile:
                user_profile = UserProfile.objects.filter(user=user).first()
                request.session['show_toast'] = True
                if user_profile:
                    request.session['privilege_history'] = user_profile.privilege_history
                    
            print(f"User login {user.username} logged in successfully.")

            # ✅ บันทึก Log สำเร็จ
            create_user_log(
                user=user,
                action="Login",
                detail=f"Username: {user.username} login success",
                status="success",
                request=request
            )

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
                'refresh': str(refresh),
                'username': user.username,
                'csrfToken': csrf_token,
                'message': 'Login successful',
                'role': role,
            })
            try:
                secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
                samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
                resp.set_cookie(getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken'), csrf_token, secure=secure, samesite=samesite)
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
