from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.contrib.sessions.models import Session

User = get_user_model()
try:
    u = User.objects.get(username='svadmin')
except Exception as e:
    print('ERROR: cannot find user svadmin:', e)
    raise

ots = OutstandingToken.objects.filter(user=u)
print('Outstanding tokens total:', ots.count())
newly_blacklisted = 0
for t in ots:
    try:
        bt, created = BlacklistedToken.objects.get_or_create(token=t)
        if created:
            newly_blacklisted += 1
        print(f'OT id={t.id} jti={t.jti} expires={t.expires_at} blacklisted_now={created}')
    except Exception as e:
        print('ERROR blacklisting token id=', getattr(t, 'id', None), e)

# delete sessions for user
removed_sessions = 0
for s in Session.objects.all():
    try:
        data = s.get_decoded()
        if data.get('_auth_user_id') == str(u.id):
            s.delete()
            removed_sessions += 1
    except Exception:
        pass

print('newly_blacklisted:', newly_blacklisted)
print('sessions_removed:', removed_sessions)
print('done')
