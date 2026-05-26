import os
import json
from django.db import migrations, connection

def seed_permissions(apps, schema_editor):
    UserPermission = apps.get_model('configuration', 'UserPermission')
    UserPermissionType = apps.get_model('configuration', 'UserPermissionType')
    UserPermissionAction = apps.get_model('configuration', 'UserPermissionAction')
    UserPermissionDetail = apps.get_model('configuration', 'UserPermissionDetail')

    # Truncate tables to be sure
    UserPermissionDetail.objects.all().delete()
    UserPermission.objects.all().delete()
    UserPermissionAction.objects.all().delete()
    UserPermissionType.objects.all().delete()

    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER SEQUENCE tb_user_permission_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE tb_user_permission_detail_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE tb_user_permission_action_id_seq RESTART WITH 1;")
            cursor.execute("ALTER SEQUENCE tb_user_permission_type_id_seq RESTART WITH 1;")
        except Exception:
            pass

    # 1. Seed Types
    types_data = [
        (1, 'access'),
        (2, 'Audio Records'),
        (3, 'Management'),
        (4, 'Role & Permissions'),
        (5, 'Group & Team'),
        (6, 'Ticket'),
        (7, 'Logs'),
        (8, 'Setting')
    ]
    for id_val, name in types_data:
        UserPermissionType(id=id_val, name=name).save()

    # 2. Seed Actions (with explicit IDs to ensure stability)
    actions_data = [
        # access (1 to 11)
        (1, 'Audio Records', 1),
        (2, 'User Management', 1),
        (3, 'Delegate Management', 1),
        (4, 'Ticket Management', 1),
        (5, 'Role & Permissions', 1),
        (6, 'Group & Team', 1),
        (7, 'System Log', 1),
        (8, 'Audit Log', 1),
        (9, 'Ticket History', 1),
        (10, 'Setting', 1),
        (11, 'User Profile', 1),
        # Audio Records (12 to 16)
        (12, 'Query Audio Records', 2),
        (13, 'Playback Audio Records', 2),
        (14, 'Download Audio Records', 2),
        (15, 'Save as Audio Index', 2),
        (16, 'Delegate Files', 2),
        # Management (17 to 26)
        (17, 'Add User', 3),
        (18, 'Edit User', 3),
        (19, 'Delete User', 3),
        (20, 'Change User Status', 3),
        (21, 'Reset User Password', 3),
        (22, 'Save As User Index', 3),
        (23, 'Create Delegate', 3),
        (24, 'Playback Delegate File', 3),
        (25, 'Download Delegate File', 3),
        (26, 'Change Delegate Status', 3),
        # Role & Permissions (27 to 30)
        (27, 'Edit Base Role', 4),
        (28, 'Add Custom Role', 4),
        (29, 'Edit Custom Role', 4),
        (30, 'Delete Custom Role', 4),
        # Group & Team (31 to 36)
        (31, 'Add Group', 5),
        (32, 'Edit Group', 5),
        (33, 'Delete Group', 5),
        (34, 'Add Team', 5),
        (35, 'Edit Team', 5),
        (36, 'Delete Team', 5),
        # Ticket (37 to 41)
        (37, 'Create Ticket', 6),
        (38, 'Playback Ticket File', 6),
        (39, 'Download Ticket File', 6),
        (40, 'Change Ticket Status', 6),
        (41, 'Ticket Reset', 6),
        # Logs (42 to 44)
        (42, 'Save As System Log', 7),
        (43, 'Save As Audit Log', 7),
        (44, 'Save As Ticket History', 7),
        # Setting (45 to 46)
        (45, 'Set Column', 8),
        (46, 'Download Player', 8)
    ]
    actions_instances = {}
    for id_val, name, type_id in actions_data:
        act = UserPermissionAction(id=id_val, name=name)
        act.save()
        actions_instances[id_val] = (act, type_id)

    # 3. Seed Roles
    roles_data = [
        (1, 'administrator', 'Administrator'),
        (2, 'auditor', 'Auditor'),
        (3, 'operator', 'Operator'),
        (4, 'ticket', 'Ticket'),
        (6, 'custom', 'Custom Role 6'),
        (7, 'custom', 'Custom Role 7'),
        (8, 'custom', 'Custom Role 8'),
        (9, 'custom', 'Custom Role 9'),
        (10, 'custom', 'Custom Role 10'),
        (11, 'custom', 'Custom Role 11'),
        (13, 'custom', 'Custom Role 13'),
        (16, 'custom', 'Custom Role 16'),
        (17, 'custom', 'Custom Role 17'),
        (18, 'custom', 'Custom Role 18'),
    ]
    roles_instances = {}
    for id_val, rtype, name in roles_data:
        role = UserPermission(id=id_val, type=rtype, name=name)
        role.save()
        roles_instances[id_val] = role

    # 4. Seed Details
    admin_active = set(range(1, 47))
    auditor_active = {1, 8, 12, 13, 14, 15, 37, 38, 39, 40, 41, 43, 45}
    operator_active = {1, 12, 13, 37, 38, 39, 40, 41, 45}
    ticket_active = {1, 13, 37, 38, 39, 40, 41}

    active_map = {
        1: admin_active,
        2: auditor_active,
        3: operator_active,
        4: ticket_active,
        6: set(),
        7: set(),
        8: set(),
        9: set(),
        10: set(),
        11: set(),
        13: set(),
        16: set(),
        17: set(),
        18: set(),
    }

    details = []
    for role_id, role_obj in roles_instances.items():
        active_set = active_map[role_id]
        for act_id, (act_obj, type_id) in actions_instances.items():
            is_active = act_id in active_set
            details.append(UserPermissionDetail(
                user_permission=role_obj,
                action=act_obj,
                status=is_active,
                type_id=type_id,
                default=is_active
            ))
    UserPermissionDetail.objects.bulk_create(details)

    # Set PostgreSQL sequence values to max ID to prevent future clashes
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT setval('tb_user_permission_id_seq', COALESCE((SELECT MAX(id) FROM tb_user_permission), 1));")
            cursor.execute("SELECT setval('tb_user_permission_detail_id_seq', COALESCE((SELECT MAX(id) FROM tb_user_permission_detail), 1));")
            cursor.execute("SELECT setval('tb_user_permission_action_id_seq', COALESCE((SELECT MAX(id) FROM tb_user_permission_action), 1));")
            cursor.execute("SELECT setval('tb_user_permission_type_id_seq', COALESCE((SELECT MAX(id) FROM tb_user_permission_type), 1));")
        except Exception as e:
            print(f"Error resetting sequences: {e}")

    # 5. Restore userauth mappings from JSON backup
    backup_path = r"C:\Users\ACER\.gemini\antigravity\brain\579f413d-faf0-4f56-8fe8-f6a595971270\scratch\mappings_backup.json"
    if os.path.exists(backup_path):
        try:
            with open(backup_path, 'r') as f:
                mappings = json.load(f)
            with connection.cursor() as cursor:
                for auth_id, perm_id in mappings:
                    cursor.execute("UPDATE tb_userauth SET user_permisson_id = %s WHERE id = %s;", [perm_id, auth_id])
            print(f"Restored {len(mappings)} userauth references successfully.")
        except Exception as e:
            print(f"Error restoring mappings: {e}")

def reverse_seed(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('configuration', '0002_userpermissionaction_userpermissiontype_and_more'),
    ]
    operations = [
        migrations.RunPython(seed_permissions, reverse_seed),
    ]
