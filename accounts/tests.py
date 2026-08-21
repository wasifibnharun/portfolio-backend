from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.owner_password = "OwnerTestPassword!934"
        self.normal_password = "NormalTestPassword!934"

        self.owner = User.objects.create_superuser(
            username="testowner",
            email="owner@example.com",
            password=self.owner_password,
        )
        self.normal_user = User.objects.create_user(
            username="normaluser",
            email="normal@example.com",
            password=self.normal_password,
        )

    def login_owner(self):
        return self.client.post(
            reverse("accounts:login"),
            {
                "username": self.owner.username,
                "password": self.owner_password,
            },
            format="json",
        )

    def authenticate_owner(self):
        login_response = self.login_owner()
        access = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        return login_response

    def test_owner_can_log_in(self):
        response = self.login_owner()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(
            response.data["user"]["username"],
            self.owner.username,
        )
        self.assertTrue(response.data["user"]["is_superuser"])

    def test_wrong_credentials_return_same_generic_error(self):
        wrong_password_response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.owner.username,
                "password": "WrongPassword!934",
            },
            format="json",
        )

        nonexistent_user_response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "missing-user",
                "password": "WrongPassword!934",
            },
            format="json",
        )

        self.assertEqual(
            wrong_password_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            nonexistent_user_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            wrong_password_response.data,
            nonexistent_user_response.data,
        )

    def test_normal_user_cannot_use_owner_login(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.normal_user.username,
                "password": self.normal_password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_registration_endpoint_does_not_exist(self):
        response = self.client.post(
            "/api/auth/register/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonymous_user_cannot_access_me(self):
        response = self.client.get(
            reverse("accounts:me")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_owner_can_access_me(self):
        self.authenticate_owner()

        response = self.client.get(
            reverse("accounts:me")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["username"],
            self.owner.username,
        )

    def test_refresh_endpoint_returns_new_access_token(self):
        login_response = self.login_owner()

        response = self.client.post(
            reverse("accounts:refresh"),
            {
                "refresh": login_response.data["refresh"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.authenticate_owner()
        refresh = login_response.data["refresh"]

        logout_response = self.client.post(
            reverse("accounts:logout"),
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_200_OK,
        )

        refresh_response = self.client.post(
            reverse("accounts:refresh"),
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_owner_can_change_password(self):
        self.authenticate_owner()

        new_password = "NewOwnerPassword!729"

        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "old_password": self.owner_password,
                "new_password": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.owner.refresh_from_db()
        self.assertTrue(
            self.owner.check_password(new_password)
        )

    def test_wrong_old_password_is_rejected(self):
        self.authenticate_owner()

        response = self.client.post(
            reverse("accounts:change-password"),
            {
                "old_password": "WrongOldPassword!123",
                "new_password": "NewOwnerPassword!729",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("old_password", response.data)