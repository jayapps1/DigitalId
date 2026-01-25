from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user

        return (
            user.is_authenticated and
            user.is_staff and
            user.role in [
                "STATION_ADMIN",
                "REGIONAL_ADMIN",
                "SUPERADMIN",
            ]
        )
