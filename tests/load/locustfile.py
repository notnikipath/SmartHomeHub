from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def dashboard(self):
        self.client.get("/dashboard/HOME-DEMO/USR-OWNER-1")

    @task(1)
    def process_command(self):
        self.client.post(
            "/workflow/process-command",
            json={
                "user_id": "USR-OWNER-1",
                "home_id": "HOME-DEMO",
                "source": "voice",
                "command_text": "turn off living room light",
                "actor_role": "owner",
            },
        )