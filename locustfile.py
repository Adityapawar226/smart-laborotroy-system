"""
Read-only Locust load test for Diagnora.

Tests authenticated dashboard and reports pages.
Do not use for production stress testing.
"""

import os
from urllib.parse import urlparse

from locust import HttpUser, between, task
from locust.exception import StopUser


class DiagnoraReadOnlyUser(HttpUser):

    wait_time = between(2, 4)

    def on_start(self):

        lab_id = os.getenv("DIAGNORA_LAB_ID", "").strip()
        username = os.getenv("DIAGNORA_USERNAME", "").strip()
        password = os.getenv("DIAGNORA_PASSWORD", "")

        if not all((lab_id, username, password)):
            raise RuntimeError(
                "Set DIAGNORA_LAB_ID, DIAGNORA_USERNAME "
                "and DIAGNORA_PASSWORD before starting Locust."
            )

        login_successful = False

        with self.client.post(
            "/login",
            data={
                "lab_id": lab_id,
                "username": username,
                "password": password,
            },
            name="POST /login",
            allow_redirects=True,
            catch_response=True
        ) as response:

            final_path = urlparse(response.url).path.rstrip("/")

            if (
                response.status_code != 200
                or final_path != "/dashboard"
            ):
                response.failure(
                    f"Login failed: HTTP {response.status_code}, "
                    f"final page: {final_path}"
                )
            else:
                response.success()
                login_successful = True

        if not login_successful:
            raise StopUser("Authentication failed.")

    def check_authenticated_page(self, path, request_name):

        with self.client.get(
            path,
            name=request_name,
            allow_redirects=True,
            catch_response=True
        ) as response:

            final_path = urlparse(response.url).path.rstrip("/")

            if response.status_code != 200:
                response.failure(
                    f"Unexpected HTTP status: {response.status_code}"
                )

            elif final_path == "/login":
                response.failure(
                    "Session lost: redirected to login page."
                )

            else:
                response.success()

    @task(5)
    def dashboard(self):

        self.check_authenticated_page(
            "/dashboard",
            "GET /dashboard"
        )

    @task(2)
    def reports_management(self):

        self.check_authenticated_page(
            "/reports-management",
            "GET /reports-management"
        )