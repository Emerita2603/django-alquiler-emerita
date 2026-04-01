from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy


class VistaPrivadaMixin(LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")
    redirect_field_name = "next"


class VistaConPermisoMixin(VistaPrivadaMixin, PermissionRequiredMixin):
    raise_exception = True