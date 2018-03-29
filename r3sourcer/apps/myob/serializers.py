from rest_framework import serializers

from r3sourcer.apps.myob.models import MYOBCompanyFile, MYOBAuthData


class MYOBCompanyFileSerializer(serializers.ModelSerializer):
    # id = serializers.CharField()  # TODO: uncomment when frontend is done
    # cf_id = serializers.CharField()
    id = serializers.CharField(source='cf_id')
    uri = serializers.CharField(source='cf_uri')
    name = serializers.CharField(source='cf_name')

    class Meta:
        model = MYOBCompanyFile
        # fields = ('id', 'cf_id', 'uri', 'name', 'authenticated')  # TODO: uncomment when frontend is done
        fields = ('id', 'uri', 'name', 'authenticated')


class MYOBAuthDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MYOBAuthData
        fields = ("id", "myob_user_username")
