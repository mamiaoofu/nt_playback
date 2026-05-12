from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from ldap3 import Server, Connection, SIMPLE, ALL
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError

User = get_user_model()

class ActiveDirectoryBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # 1. Fetch AD config
        ad_server_uri = getattr(settings, 'AD_SERVER_URI', None)
        ad_domain = getattr(settings, 'AD_DOMAIN', None)

        if not ad_server_uri or not ad_domain:
            return None

        # 2. Use UPN format: username@domain (SIMPLE bind)
        # This is more compatible than NTLM for most AD setups
        user_principal = f"{username}@{ad_domain}"

        # 3. Connect and Bind to AD using SIMPLE authentication
        server = Server(ad_server_uri, get_info=ALL)
        try:
            conn = Connection(
                server,
                user=user_principal,
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )
            # If auto_bind succeeds, password is correct
            conn.unbind()
        except LDAPBindError as e:
            err_str = str(e).lower()
            # Check for "must change password" situation
            if 'must change password' in err_str or 'data 773' in err_str:
                print(f"ActiveDirectoryBackend: User {username} must change password at next logon.")
            else:
                print(f"ActiveDirectoryBackend: Invalid credentials for {username}: {e}")
            return None
        except LDAPSocketOpenError:
            print(f"ActiveDirectoryBackend: Cannot connect to AD server at {ad_server_uri}")
            return None
        except Exception as e:
            print(f"ActiveDirectoryBackend Error: {type(e).__name__}: {e}")
            return None

        # 4. If AD auth succeeds, check if the user exists in Django DB
        try:
            user = User.objects.get(username__iexact=username)
            return user
        except User.DoesNotExist:
            print(f"ActiveDirectoryBackend: User {username} authenticated via AD but does not exist in Django DB.")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
