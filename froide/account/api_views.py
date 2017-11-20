from rest_framework import serializers, views, permissions, response

from oauth2_provider.contrib.rest_framework import TokenHasScope

from .models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id',)

    def to_representation(self, obj):
        default = super(UserSerializer, self).to_representation(obj)
        if obj.is_superuser:
            default['is_superuser'] = True
        if obj.is_staff:
            default['is_staff'] = True
        return default


class UserDetailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + ('first_name', 'last_name',)


class UserEmailSerializer(UserSerializer):
    class Meta:
        model = User
        fields = UserDetailSerializer.Meta.fields + ('email',)


class ProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['read:user']

    def get(self, request, format=None):
        token = request.auth
        user = request.user
        if token.is_valid(['read:email']):
            serializer = UserEmailSerializer(user)
        elif token.is_valid(['read:profile']):
            serializer = UserDetailSerializer(user)
        else:
            serializer = UserSerializer(user)
        return response.Response(serializer.data)
