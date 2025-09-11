from rest_framework import serializers
from .models import CoreLevelPartyMember

class CoreLevelPartyMemberSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoreLevelPartyMember
        fields = [
            'id', 'username', 'email', 'phone', 'address',
            'role', 'is_active', 'valid_until', 'is_valid'
        ]
        read_only_fields = ['is_valid']

    def get_is_valid(self, obj):
        return obj.is_valid()
