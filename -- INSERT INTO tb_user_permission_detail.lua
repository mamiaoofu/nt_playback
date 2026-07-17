-- INSERT INTO tb_user_permission

INSERT INTO "tb_user_permission" ("id", "type", "name", "create_date", "update_date") VALUES (1, 'administrator', 'Administrator', '2025-12-22 15:00:55+07', '2026-01-15 09:00:54.55704+07');
INSERT INTO "tb_user_permission" ("id", "type", "name", "create_date", "update_date") VALUES (2, 'auditor', 'Auditor', '2025-12-22 15:21:02+07', '2026-02-03 11:29:25.435529+07');
INSERT INTO "tb_user_permission" ("id", "type", "name", "create_date", "update_date") VALUES (3, 'operator', 'Operator', '2025-12-22 15:21:14+07', '2026-01-08 14:31:29.006284+07');
INSERT INTO "tb_user_permission" ("id", "type", "name", "create_date", "update_date") VALUES (4, 'ticket', 'Ticket', '2026-02-18 20:55:44.776134+07', '2026-04-01 15:02:21.488659+07');

-- INSERT INTO tb_user_permission_detail 
-- ALTER SEQUENCE tb_user_permission_detail_id_seq RESTART WITH 1;

INSERT INTO tb_user_permission_detail ( "user_permission_id", "action", "status", "default", "type") VALUES
-- user_permission_id = 1 
(1,'Audio Records','t','t','access'),
(1,'User Management','t','t','access'),
(1,'Delegate Management','t','t','access'),
(1,'Ticket Management','t','t','access'),
(1,'Role & Permissions','t','t','access'),
(1,'Group & Team','t','t','access'),
(1,'System Log','t','t','access'),
(1,'Audit Log','t','t','access'),
(1,'Ticket History','t','t','access'),
(1,'Setting','t','t','access'),
(1,'User Profile','t','t','access'),

(1,'Query Audio Records','t','t','Audio Records'),
(1,'Playback Audio Records','t','t','Audio Records'),
(1,'Download Audio Records','t','t','Audio Records'),
(1,'Save as Audio Index','t','t','Audio Records'),
(1,'Delegate Files','t','t','Audio Records'),

(1,'Add User','t','t','Management'),
(1,'Edit User','t','t','Management'),
(1,'Delete User','t','t','Management'),
(1,'Change User Status','t','t','Management'),
(1,'Reset User Password','t','t','Management'),
(1,'Save as User Index','t','t','Management'),
(1,'Create Delegate','t','t','Management'),
(1,'Playback Delegate File','t','t','Management'),
(1,'Download Delegate File','t','t','Management'),
(1,'Change Delegate Status','t','t','Management'),

(1,'Edit Base Role','t','t','Role & Permissions'),
(1,'Add Custom Role','t','t','Role & Permissions'),
(1,'Edit Custom Role','t','t','Role & Permissions'),
(1,'Delete Custom Role','t','t','Role & Permissions'),

(1,'Add Group','t','t','Group & Team'),
(1,'Edit Group','t','t','Group & Team'),
(1,'Delete Group','t','t','Group & Team'),
(1,'Add Team','t','t','Group & Team'),
(1,'Edit Team','t','t','Group & Team'),
(1,'Delete Team','t','t','Group & Team'),

(1,'Create Ticket','t','t','Ticket'),
(1,'Playback Ticket File','t','t','Ticket'),
(1,'Download Ticket File','t','t','Ticket'),
(1,'Change Ticket Status','t','t','Ticket'),
(1,'Ticket Reset','t','t','Ticket'),

(1,'Save as System Log','t','t','Logs'),
(1,'Save as Audit Log','t','t','Logs'),
(1,'Save as Ticket History','t','t','Logs'),

(1,'Set Column','t','t','Setting'),
(1,'Download Player','t','t','Setting'),

-- user_permission_id = 2 
(2,'Audio Records','t','t','access'),
(2,'User Management','f','f','access'),
(2,'Delegate Management','f','f','access'),
(2,'Ticket Management','f','f','access'),
(2,'Role & Permissions','f','f','access'),
(2,'Group & Team','f','f','access'),
(2,'System Log','f','f','access'),
(2,'Audit Log','t','t','access'),
(2,'Ticket History','f','f','access'),
(2,'Setting','f','f','access'),
(2,'User Profile','f','f','access'),

(2,'Query Audio Records','t','t','Audio Records'),
(2,'Playback Audio Records','t','t','Audio Records'),
(2,'Download Audio Records','t','t','Audio Records'),
(2,'Save as Audio Index','t','t','Audio Records'),
(2,'Delegate Files','f','f','Audio Records'),

(2,'Add User','f','f','Management'),
(2,'Edit User','f','f','Management'),
(2,'Delete User','f','f','Management'),
(2,'Change User Status','f','f','Management'),
(2,'Reset User Password','f','f','Management'),
(2,'Save as User Index','f','f','Management'),
(2,'Create Delegate','f','f','Management'),
(2,'Playback Delegate File','f','f','Management'),
(2,'Download Delegate File','f','f','Management'),
(2,'Change Delegate Status','f','f','Management'),

(2,'Edit Base Role','f','f','Role & Permissions'),
(2,'Add Custom Role','f','f','Role & Permissions'),
(2,'Edit Custom Role','f','f','Role & Permissions'),
(2,'Delete Custom Role','f','f','Role & Permissions'),

(2,'Add Group','f','f','Group & Team'),
(2,'Edit Group','f','f','Group & Team'),
(2,'Delete Group','f','f','Group & Team'),
(2,'Add Team','f','f','Group & Team'),
(2,'Edit Team','f','f','Group & Team'),
(2,'Delete Team','f','f','Group & Team'),

(2,'Create Ticket','t','t','Ticket'),
(2,'Playback Ticket File','t','t','Ticket'),
(2,'Download Ticket File','t','t','Ticket'),
(2,'Change Ticket Status','t','t','Ticket'),
(2,'Ticket Reset','t','t','Ticket'),

(2,'Save as System Log','f','f','Logs'),
(2,'Save as Audit Log','t','t','Logs'),
(2,'Save as Ticket History','f','f','Logs'),

(2,'Set Column','t','t','Setting'),
(2,'Download Player','f','f','Setting'),

-- user_permission_id = 3
(3,'Audio Records','t','t','access'),
(3,'User Management','f','f','access'),
(3,'Delegate Management','f','f','access'),
(3,'Ticket Management','f','f','access'),
(3,'Role & Permissions','f','f','access'),
(3,'Group & Team','f','f','access'),
(3,'System Log','f','f','access'),
(3,'Audit Log','f','f','access'),
(3,'Ticket History','f','f','access'),
(3,'Setting','f','f','access'),
(3,'User Profile','f','f','access'),

(3,'Query Audio Records','t','t','Audio Records'),
(3,'Playback Audio Records','t','t','Audio Records'),
(3,'Download Audio Records','f','f','Audio Records'),
(3,'Save as Audio Index','f','f','Audio Records'),
(3,'Delegate Files','f','f','Audio Records'),

(3,'Add User','f','f','Management'),
(3,'Edit User','f','f','Management'),
(3,'Delete User','f','f','Management'),
(3,'Change User Status','f','f','Management'),
(3,'Reset User Password','f','f','Management'),
(3,'Save as User Index','f','f','Management'),
(3,'Create Delegate','f','f','Management'),
(3,'Playback Delegate File','f','f','Management'),
(3,'Download Delegate File','f','f','Management'),
(3,'Change Delegate Status','f','f','Management'),

(3,'Edit Base Role','f','f','Role & Permissions'),
(3,'Add Custom Role','f','f','Role & Permissions'),
(3,'Edit Custom Role','f','f','Role & Permissions'),
(3,'Delete Custom Role','f','f','Role & Permissions'),

(3,'Add Group','f','f','Group & Team'),
(3,'Edit Group','f','f','Group & Team'),
(3,'Delete Group','f','f','Group & Team'),
(3,'Add Team','f','f','Group & Team'),
(3,'Edit Team','f','f','Group & Team'),
(3,'Delete Team','f','f','Group & Team'),

(3,'Create Ticket','t','t','Ticket'),
(3,'Playback Ticket File','t','t','Ticket'),
(3,'Download Ticket File','t','t','Ticket'),
(3,'Change Ticket Status','t','t','Ticket'),
(3,'Ticket Reset','t','t','Ticket'),

(3,'Save as System Log','f','f','Logs'),
(3,'Save as Audit Log','f','f','Logs'),
(3,'Save as Ticket History','f','f','Logs'),

(3,'Set Column','t','t','Setting'),
(3,'Download Player','f','f','Setting'),

-- user_permission_id = 4
(4,'Audio Records','t','t','access'),
(4,'User Management','f','f','access'),
(4,'Delegate Management','f','f','access'),
(4,'Ticket Management','f','f','access'),
(4,'Role & Permissions','f','f','access'),
(4,'Group & Team','f','f','access'),
(4,'System Log','f','f','access'),
(4,'Audit Log','f','f','access'),
(4,'Ticket History','f','f','access'),
(4,'Setting','f','f','access'),
(4,'User Profile','f','f','access'),

(4,'Query Audio Records','f','f','Audio Records'),
(4,'Playback Audio Records','t','t','Audio Records'),
(4,'Download Audio Records','f','f','Audio Records'),
(4,'Save as Audio Index','f','f','Audio Records'),
(4,'Delegate Files','f','f','Audio Records'),

(4,'Add User','f','f','Management'),
(4,'Edit User','f','f','Management'),
(4,'Delete User','f','f','Management'),
(4,'Change User Status','f','f','Management'),
(4,'Reset User Password','f','f','Management'),
(4,'Save as User Index','f','f','Management'),
(4,'Create Delegate','f','f','Management'),
(4,'Playback Delegate File','f','f','Management'),
(4,'Download Delegate File','f','f','Management'),
(4,'Change Delegate Status','f','f','Management'),

(4,'Edit Base Role','f','f','Role & Permissions'),
(4,'Add Custom Role','f','f','Role & Permissions'),
(4,'Edit Custom Role','f','f','Role & Permissions'),
(4,'Delete Custom Role','f','f','Role & Permissions'),

(4,'Add Group','f','f','Group & Team'),
(4,'Edit Group','f','f','Group & Team'),
(4,'Delete Group','f','f','Group & Team'),
(4,'Add Team','f','f','Group & Team'),
(4,'Edit Team','f','f','Group & Team'),
(4,'Delete Team','f','f','Group & Team'),

(4,'Create Ticket','t','t','Ticket'),
(4,'Playback Ticket File','t','t','Ticket'),
(4,'Download Ticket File','t','t','Ticket'),
(4,'Change Ticket Status','t','t','Ticket'),
(4,'Ticket Reset','t','t','Ticket'),

(4,'Save as System Log','f','f','Logs'),
(4,'Save as Audit Log','f','f','Logs'),
(4,'Save as Ticket History','f','f','Logs'),

(4,'Set Column','f','f','Setting'),
(4,'Download Player','f','f','Setting'),