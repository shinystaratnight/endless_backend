from rest_framework import serializers

from r3sourcer.apps.myob.models import MYOBCompanyFile


class MYOBCompanyFileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='cf_id')
    uri = serializers.CharField(source='cf_uri')
    name = serializers.CharField(source='cf_name')

    class Meta:
        model = MYOBCompanyFile
        fields = ('id', 'uri', 'name', 'authenticated')
