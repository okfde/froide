from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied
from django.db import models
from django.template.response import TemplateResponse

import pytest

from froide.helper.admin_utils import make_choose_object_action


class MockModel(models.Model):
    class Meta:
        app_label = "test_app"
        verbose_name = "Mock Model"


@pytest.fixture
def mock_model_admin():
    model_admin = Mock()
    model_admin.has_change_permission.return_value = True
    model_admin.model = MockModel
    model_admin.media = "mock_media"

    return model_admin


@pytest.fixture
def mock_request():
    request = Mock()
    request.POST = {"action": "Test Action"}
    return request


class TestMakeChooseObjectAction:
    def test_executes_callback_with_valid_form(self, mock_model_admin, mock_request):
        mock_request.POST["obj"] = "1"
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {"obj": "mock_object"}
        mock_callback = Mock()
        mock_queryset = Mock()

        with patch("froide.helper.admin_utils.get_fake_fk_form_class") as mock_get_form:
            mock_get_form.return_value = Mock(return_value=mock_form)
            action = make_choose_object_action(MockModel, mock_callback, "Test Action")
            response = action(mock_model_admin, mock_request, mock_queryset)

        assert response is None

        mock_callback.assert_called_once_with(
            mock_model_admin, mock_request, mock_queryset, "mock_object"
        )
        mock_model_admin.message_user.assert_called_once_with(
            mock_request, "Successfully executed."
        )

    def test_denies_access_without_change_permission(
        self, mock_model_admin, mock_request
    ):
        mock_model_admin.has_change_permission.return_value = False
        mock_callback = Mock()
        mock_queryset = Mock()

        action = make_choose_object_action(MockModel, mock_callback, "Test Action")

        with pytest.raises(PermissionDenied):
            action(mock_model_admin, mock_request, mock_queryset)

        mock_callback.assert_not_called()

    def test_renders_confirmation_page_with_invalid_form(
        self, mock_model_admin, mock_request
    ):
        mock_request.POST["obj"] = "1"
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_callback = Mock()
        mock_queryset = Mock()

        with patch("froide.helper.admin_utils.get_fake_fk_form_class") as mock_get_form:
            mock_get_form.return_value = Mock(return_value=mock_form)
            action = make_choose_object_action(MockModel, mock_callback, "Test Action")
            response = action(mock_model_admin, mock_request, mock_queryset)

        assert isinstance(response, TemplateResponse)
        assert response.template_name == "helper/admin/apply_action.html"
        assert len(response.context_data) == 8
        assert response.context_data["opts"] == mock_model_admin.model._meta
        assert response.context_data["queryset"] == mock_queryset
        assert response.context_data["media"] == "mock_media"
        assert response.context_data["action_checkbox_name"] == "_selected_action"
        assert response.context_data["form"] == mock_form
        assert response.context_data["headline"] == "Test Action"
        assert response.context_data["actionname"] == "Test Action"
        assert response.context_data["applabel"] == "test_app"
        mock_callback.assert_not_called()
        mock_model_admin.message_user.assert_called_once_with(
            mock_request, "Please enter a valid Mock Model ID.", level="error"
        )

    def test_renders_confirmation_page_without_obj_in_post_data(
        self, mock_model_admin, mock_request
    ):
        mock_form = Mock()
        mock_callback = Mock()
        mock_queryset = Mock()

        with patch("froide.helper.admin_utils.get_fake_fk_form_class") as mock_get_form:
            mock_get_form.return_value = Mock(return_value=mock_form)
            action = make_choose_object_action(MockModel, mock_callback, "Test Action")
            response = action(mock_model_admin, mock_request, mock_queryset)

        assert isinstance(response, TemplateResponse)
        assert response.template_name == "helper/admin/apply_action.html"
        assert len(response.context_data) == 8
        assert response.context_data["opts"] == mock_model_admin.model._meta
        assert response.context_data["queryset"] == mock_queryset
        assert response.context_data["media"] == "mock_media"
        assert response.context_data["action_checkbox_name"] == "_selected_action"
        assert response.context_data["form"] == mock_form
        assert response.context_data["headline"] == "Test Action"
        assert response.context_data["actionname"] == "Test Action"
        assert response.context_data["applabel"] == "test_app"
        mock_callback.assert_not_called()
        mock_model_admin.message_user.assert_not_called()
