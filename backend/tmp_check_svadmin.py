from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.sessions.models import Session

U = get_user_model().objects.filter(username='svadmin').first()
print('USER_ID:', U.id if U else None)
if not U:
    print('User svadmin not found')
else:
    ots = OutstandingToken.objects.filter(user=U)
    print('OUTSTANDING_COUNT:', ots.count())
    for o in ots:
        try:
            tok = getattr(o, 'token', None)
        except Exception:
            tok = None
        print('OT:', tok, 'expires:', getattr(o, 'expires_at', None), 'blacklisted:', BlacklistedToken.objects.filter(token=o).exists())

    sessions = []
    for s in Session.objects.all():
        try:
            d = s.get_decoded()
        except Exception:
            continue
        if str(d.get('_auth_user_id')) == str(U.id):
            sessions.append((s.session_key, getattr(s, 'expire_date', None)))
    print('SESSIONS:', sessions)
