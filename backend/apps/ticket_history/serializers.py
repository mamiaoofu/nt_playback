from rest_framework import serializers
from rest_framework.relations import HyperlinkedIdentityField

from apps.core.model.authorize.models import UserFileShare


class UserFileShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFileShare
        fields = '__all__'