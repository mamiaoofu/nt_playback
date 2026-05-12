from ldap3 import Server, Connection, NTLM, SIMPLE, ALL
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError

def test_ad(username, password):
    ad_server_uri = "ldap://192.168.1.8"
    
    formats = [
        (f"nichetel.local\\{username}", NTLM),
        (f"nichetel\\{username}", NTLM),
        (f"{username}@nichetel.local", SIMPLE)
    ]
    
    server = Server(ad_server_uri, get_info=ALL)
    
    for principal, auth_type in formats:
        print(f"\nTesting Principal: {principal} (Auth: {auth_type})")
        try:
            conn = Connection(
                server,
                user=principal,
                password=password,
                authentication=auth_type,
                auto_bind=True
            )
            print(">>> SUCCESS! <<<")
            conn.unbind()
        except LDAPBindError as e:
            print(f"FAILED: {e}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_ad("test_domain", "Bl@ze389")
