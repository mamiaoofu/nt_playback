from django.db import connection

def inspect_columns(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = '{table_name}';
        """)
        print(f"Columns in {table_name}:")
        for col in cursor.fetchall():
            print(f"  {col[0]}: {col[1]} ({col[2]})")

inspect_columns('tb_audiofile')
inspect_columns('tb_audioinfo')
