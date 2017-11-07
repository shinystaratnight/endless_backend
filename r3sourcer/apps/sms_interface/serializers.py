import json

from django.contrib.contenttypes.models import ContentType
from .models import SMSTemplate
from rest_framework import serializers


class TemplateBodySerializer(serializers.Serializer):

    body = serializers.CharField()
    params = serializers.CharField(required=False)

    def validate_params(self, validated_data):
        return json.loads(validated_data)


class ContentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'model')


class TemplateSerializer(serializers.ModelSerializer):

    required_params = serializers.SerializerMethodField()

    def get_required_params(self, obj):
        return obj.get_require_params(obj.message_html_template, obj.message_text_template, use_lookup=False)

    class Meta:
        model = SMSTemplate
        fields = '__all__'
