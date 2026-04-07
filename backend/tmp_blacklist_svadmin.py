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
blacklisted_created = 0
for t in ots:
    bt, created = BlacklistedToken.objects.get_or_create(token=t)
    if created:
        blacklisted_created += 1
print('Blacklisted tokens newly created:', blacklisted_created)

# delete sessions for user
deleted_sessions = 0
for s in Session.objects.all():
    try:
        data = s.get_decoded()
        if data.get('_auth_user_id') == str(u.id):
            s.delete()
            deleted_sessions += 1
    except Exception:
        # skip corrupted sessions
        pass
print('Sessions deleted for user:', deleted_sessions)
print('done')
