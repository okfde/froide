from collections import OrderedDict
from typing import Union

from django.utils.functional import SimpleLazyObject

from oauth2_provider.contrib.rest_framework import IsAuthenticatedOrTokenHasScope
from rest_framework import response, serializers, status, views
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import User, UserPreference
from .preferences import registry


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("id", "private")

    def to_representation(self, obj: Union[User, SimpleLazyObject]) -> OrderedDict:
        default = super(UserSerializer, self).to_representation(obj)
        if obj.is_superuser:
            default["is_superuser"] = True
        if obj.is_staff:
            default["is_staff"] = True
        return default


class UserEmailSerializer(UserSerializer):
    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + ("email",)


class UserDetailSerializer(UserSerializer):
    full_name = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + (
            "first_name",
            "last_name",
            "full_name",
            "username",
            "profile_photo",
        )

    def get_full_name(self, obj: Union[User, SimpleLazyObject]) -> str:
        return obj.get_full_name()

    def get_profile_photo(self, obj):
        if obj.profile_photo:
            return obj.profile_photo.url
        return None


class UserEmailDetailSerializer(UserDetailSerializer):
    class Meta:
        model = User
        fields = UserDetailSerializer.Meta.fields + ("email",)


class UserFullSerializer(UserEmailDetailSerializer):
    class Meta:
        model = User
        fields = UserEmailDetailSerializer.Meta.fields + ("address",)


class ProfileView(views.APIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["read:user"]

    def get(self, request: Request, format: None = None) -> Response:
        token = request.auth
        user = request.user
        if token:
            has_email = token.is_valid(["read:email"])
            has_profile = token.is_valid(["read:profile"])
            if has_email and has_profile:
                serializer = UserEmailDetailSerializer(user)
            elif has_email:
                serializer = UserEmailSerializer(user)
            elif has_profile:
                serializer = UserDetailSerializer(user)
            else:
                serializer = UserSerializer(user)
        else:
            # if token is None, user is currently logged in user
            serializer = UserFullSerializer(user)
        return response.Response(serializer.data)


class UserPreferenceSerializer(serializers.Serializer):
    value = serializers.CharField()


class UserPreferenceView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPreferenceSerializer
    lookup_url_kwarg = "key"
    lookup_field = "key"

    def post(self, request, *args, **kwargs):
        # Accept POST requests for update as well
        return self.update(request, *args, **kwargs)

    def get_queryset(self):
        key = self.kwargs["key"]
        try:
            registry.find(key)
        except KeyError:
            return UserPreference.objects.none()
        return UserPreference.objects.filter(user=self.request.user, key=key)

    def update(self, request, *args, **kwargs):
        key = self.kwargs["key"]
        try:
            form_klass = registry.find(key)
        except KeyError:
            return Response(None, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = dict(serializer.data, key=key)
        form = form_klass(data)
        if form.is_valid():
            form.save(request.user)
            return Response(None)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
