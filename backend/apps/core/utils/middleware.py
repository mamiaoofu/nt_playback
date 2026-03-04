import os
from django.conf import settings
from django.db import connections
from django.utils.deprecation import MiddlewareMixin


class DynamicDBHostMiddleware(MiddlewareMixin):
	"""
	Middleware to switch the default database HOST based on the incoming request host.

	- If request host is localhost/127.0.0.1 -> use 'host.docker.internal'
	- If request host is 192.168.1.90 -> use '192.168.1.90'

	NOTE: This mutates `settings.DATABASES` and `connections['default'].settings_dict` and
	closes the existing connection so the next DB use picks up the new host. Intended
	for local/dev setups only.
	"""

	# Mapping from incoming request host -> target DB connection settings.
	# For sensitive values prefer setting env vars and DO NOT hardcode secrets.
	# Build configs from environment variables:
	_postgres_host = os.environ.get('POSTGRES_HOST')
	_postgres_user = os.environ.get('POSTGRES_USER')
	_postgres_password = os.environ.get('POSTGRES_PASSWORD')

	_postgres_host_dev = os.environ.get('POSTGRES_HOST_DEV') or 'host.docker.internal'
	# _postgres_password_dev = os.environ.get('POSTGRES_PASSWORD_DEV')
	_postgres_password_dev = ''

	POSTGRES_PORT = os.environ.get('POSTGRES_PORT')

	HOST_CONFIG = {
		'localhost': {
			'HOST': _postgres_host_dev,
		},
		'127.0.0.1': {
			'HOST': _postgres_host_dev,
		},
	}

	# If a dev password is provided, include it for localhost
	if _postgres_password_dev:
		HOST_CONFIG['localhost']['PASSWORD'] = _postgres_password_dev
		HOST_CONFIG['127.0.0.1']['PASSWORD'] = _postgres_password_dev

	# Add production-like host if env provided
	if _postgres_host:
		_cfg_192 = {'HOST': _postgres_host}
		if _postgres_user:
			_cfg_192['USER'] = _postgres_user
		if _postgres_password:
			_cfg_192['PASSWORD'] = _postgres_password
		HOST_CONFIG['192.168.1.90'] = _cfg_192

	if POSTGRES_PORT:
		for k in list(HOST_CONFIG.keys()):
			HOST_CONFIG[k]['PORT'] = POSTGRES_PORT

	def process_request(self, request):
		host = request.get_host().split(':')[0]
		cfg = self.HOST_CONFIG.get(host)
		if not cfg:
			return None

		db_defaults = settings.DATABASES.get('default', {})

		changed = False

		# Update HOST
		new_host = cfg.get('HOST')
		if new_host and db_defaults.get('HOST') != new_host:
			settings.DATABASES['default']['HOST'] = new_host
			changed = True

		for key in ('USER', 'PASSWORD'):
			if key in cfg and db_defaults.get(key) != cfg[key]:
				settings.DATABASES['default'][key] = cfg[key]
				changed = True

		if not changed:
			return None

		try:
			conn = connections['default']
			# apply to connection settings_dict as well
			if new_host:
				conn.settings_dict['HOST'] = new_host
			if 'USER' in cfg:
				conn.settings_dict['USER'] = cfg['USER']
			if 'PASSWORD' in cfg:
				conn.settings_dict['PASSWORD'] = cfg['PASSWORD']
			conn.close()
		except Exception:
			pass

		return None

