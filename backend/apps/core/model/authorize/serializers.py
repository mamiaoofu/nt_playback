# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
import json
from .models import MainDatabase,UserAuth,UserLog,SetAudio,UserProfile,UserGroup,UserTeam

class MainDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainDatabase
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']
        
class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = '__all__'


class UserTeamSerializer(serializers.ModelSerializer):
    user_group = UserGroupSerializer(read_only=True)
    maindatabase = serializers.CharField(read_only=True)
    maindatabase_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserTeam
        fields = '__all__'

    def get_maindatabase_name(self, obj):
        raw = getattr(obj, 'maindatabase', None)
        if not raw:
            return []
        try:
            ids = json.loads(raw)
        except Exception:
            # fallback: if it's a single id string
            ids = [raw]
        try:
            ids = [int(i) for i in ids]
        except Exception:
            pass
        qs = MainDatabase.objects.filter(id__in=ids)
        names = [m.database_name for m in qs]
        return names

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    team = UserTeamSerializer(read_only=True)
    is_active = serializers.BooleanField(
        source='user.is_active',
        read_only=True
    )

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'team', 'user_code', 'phone', 'create_at', 'update_at', 'is_active', 'ad_account']


class UserAuthSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    maindatabase = MainDatabaseSerializer(read_only=True)

    class Meta:
        model = UserAuth
        fields = ['id', 'user', 'maindatabase', 'privilege']

class UserLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    audiofile_id = serializers.IntegerField(source='audiofile.id', read_only=True)

    class Meta:
        model = UserLog
        fields = ['id', 'user', 'action', 'timestamp', 'detail', 'ip_address', 'audiofile_id']

class SetAudioSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SetAudio
        fields = ['id', 'user', 'audio_path', 'create_at', 'update_at']





