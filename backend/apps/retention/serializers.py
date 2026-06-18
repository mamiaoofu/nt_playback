from rest_framework import serializers
from .models import RetentionTask, RetentionLog, AutoRetentionConfig

class RetentionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionTask
        fields = '__all__'

class RetentionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionLog
        fields = '__all__'

class AutoRetentionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoRetentionConfig
        fields = '__all__'
