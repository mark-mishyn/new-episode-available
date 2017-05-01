from rest_framework import serializers


class HandleVkRequestSerializer(serializers.Serializer):
    type = serializers.CharField()
    object = serializers.JSONField(required=False)
