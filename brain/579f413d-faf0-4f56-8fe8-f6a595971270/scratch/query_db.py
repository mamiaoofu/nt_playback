import os
import sys
import django

sys.path.append(r"c:\Users\ACER\Documents\GitHub\nt_playback\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def run():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT action FROM tb_userlog ORDER BY action;")
        print("DISTINCT ACTIONS IN USER LOG:")
        for row in cursor.fetchall():
            print(" -", row[0])
            
        print("\nLOGS RELATED TO ROLES:")
        cursor.execute("SELECT timestamp, action, detail FROM tb_userlog WHERE action ILIKE '%role%' OR detail ILIKE '%role%' ORDER BY timestamp DESC LIMIT 50;")
        for row in cursor.fetchall():
            print(f"[{row[0]}] Action: {row[1]} | Detail: {row[2]}")

if __name__ == '__main__':
    run()
