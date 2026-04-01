import datetime
import random

from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AlquilerCreateForm, MarcarPagadoForm, SimularVentasForm
from .mixins import VistaPrivadaMixin
from .models import Alquiler, Categoria, Cliente, Pelicula


def index(request: HttpRequest) -> HttpResponse:
    total_peliculas = Pelicula.objects.count()
    total_clientes = Cliente.objects.count()
    alquileres_pendientes = Alquiler.objects.filter(pagado=False).count()
    ingresos = (
        Alquiler.objects.filter(pagado=True)
        .aggregate(total=Sum("precio"))
        .get("total")
        or 0
    )

    return render(
        request,
        "tienda/index.html",
        {
            "total_peliculas": total_peliculas,
            "total_clientes": total_clientes,
            "alquileres_pendientes": alquileres_pendientes,
            "ingresos": ingresos,
        },
    )


class CategoriaListView(VistaPrivadaMixin, ListView):
    model = Categoria
    template_name = "tienda/categoria_list.html"
    context_object_name = "categorias"


class CategoriaCreateView(VistaPrivadaMixin, CreateView):
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaUpdateView(VistaPrivadaMixin, UpdateView):
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaDeleteView(VistaPrivadaMixin, DeleteView):
    model = Categoria
    template_name = "tienda/categoria_confirm_delete.html"
    success_url = reverse_lazy("categoria_list")


class ClienteListView(VistaPrivadaMixin, ListView):
    model = Cliente
    template_name = "tienda/cliente_list.html"
    context_object_name = "clientes"


class ClienteCreateView(VistaPrivadaMixin, CreateView):
    model = Cliente
    fields = ["nombre", "email", "telefono"]
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


class ClienteUpdateView(VistaPrivadaMixin, UpdateView):
    model = Cliente
    fields = ["nombre", "email", "telefono"]
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


class ClienteDeleteView(VistaPrivadaMixin, DeleteView):
    model = Cliente
    template_name = "tienda/cliente_confirm_delete.html"
    success_url = reverse_lazy("cliente_list")


class PeliculaListView(VistaPrivadaMixin, ListView):
    model = Pelicula
    template_name = "tienda/pelicula_list.html"
    context_object_name = "peliculas"

    def get_queryset(self):
        return super().get_queryset().select_related("categoria")


class PeliculaCreateView(VistaPrivadaMixin, CreateView):
    model = Pelicula
    fields = ["titulo", "slug", "anio", "categoria", "precio_alquiler", "stock"]
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaUpdateView(VistaPrivadaMixin, UpdateView):
    model = Pelicula
    fields = ["titulo", "slug", "anio", "categoria", "precio_alquiler", "stock"]
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaDeleteView(VistaPrivadaMixin, DeleteView):
    model = Pelicula
    template_name = "tienda/pelicula_confirm_delete.html"
    success_url = reverse_lazy("pelicula_list")


class AlquilerCreateView(VistaPrivadaMixin, CreateView):
    model = Alquiler
    form_class = AlquilerCreateForm
    template_name = "tienda/alquiler_form.html"
    success_url = reverse_lazy("alquiler_list")

    def form_valid(self, form):
        with transaction.atomic():
            pelicula = Pelicula.objects.select_for_update().get(pk=form.cleaned_data["pelicula"].pk)

            if pelicula.stock < 2:
                form.add_error("pelicula", "No hay stock suficiente para alquilar esta película.")
                return self.form_invalid(form)

            self.object = form.save(commit=False)
            self.object.precio = pelicula.precio_alquiler
            self.object.save()

            pelicula.stock = F("stock") - 1
            pelicula.save(update_fields=["stock"])

        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.request.GET.get("next") or super().get_success_url()


class AlquilerListView(VistaPrivadaMixin, ListView):
    model = Alquiler
    template_name = "tienda/alquiler_list.html"
    context_object_name = "alquileres"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "pelicula", "pelicula__categoria")
        pagado = self.request.GET.get("pagado")
        if pagado == "1":
            qs = qs.filter(pagado=True)
        elif pagado == "0":
            qs = qs.filter(pagado=False)
        return qs


class MarcarPagadoView(VistaPrivadaMixin, View):
    template_name = "tienda/marcar_pagado.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        alquiler = get_object_or_404(Alquiler, pk=pk)
        form = MarcarPagadoForm()
        return render(request, self.template_name, {"alquiler": alquiler, "form": form})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        alquiler = get_object_or_404(Alquiler, pk=pk)
        form = MarcarPagadoForm(request.POST)
        if form.is_valid():
            alquiler.marcar_pagado(fecha_devolucion=form.cleaned_data.get("fecha_devolucion"))

            next_url = request.GET.get("next")
            return redirect(next_url or "alquiler_list")

        return render(request, self.template_name, {"alquiler": alquiler, "form": form})


class VentasListView(VistaPrivadaMixin, ListView):
    model = Alquiler
    template_name = "tienda/ventas_list.html"
    context_object_name = "ventas"

    def get_queryset(self):
        return (
            Alquiler.objects.filter(pagado=True)
            .select_related("cliente", "pelicula", "pelicula__categoria")
            .order_by("-fecha_alquiler")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_ingresos"] = self.get_queryset().aggregate(total=Sum("precio")).get("total") or 0
        return ctx


def simular_ventas(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SimularVentasForm(request.POST)
        if form.is_valid():
            numero = form.cleaned_data["numero_ventas"]
            desde = form.cleaned_data["desde"]
            hasta = form.cleaned_data["hasta"]

            clientes = list(Cliente.objects.all())
            peliculas = list(Pelicula.objects.all())

            if not clientes or not peliculas:
                return render(
                    request,
                    "tienda/simular_ventas.html",
                    {"form": form, "error": "Necesitas al menos 1 cliente y 1 película para simular."},
                )

            delta_dias = (hasta - desde).days if hasta >= desde else 0

            for _ in range(numero):
                cliente = random.choice(clientes)
                pelicula = random.choice(peliculas)

                offset = random.randint(0, max(delta_dias, 0))
                fecha_alquiler = desde + datetime.timedelta(days=offset)
                fecha_devolucion = fecha_alquiler + datetime.timedelta(days=random.randint(0, 7))

                Alquiler.objects.create(
                    cliente=cliente,
                    pelicula=pelicula,
                    fecha_alquiler=fecha_alquiler,
                    pagado=True,
                    fecha_devolucion=fecha_devolucion,
                )

            return redirect("ventas_list")

    else:
        form = SimularVentasForm(
            initial={
                "numero_ventas": 10,
                "desde": timezone.localdate(),
                "hasta": timezone.localdate(),
            }
        )

    return render(request, "tienda/simular_ventas.html", {"form": form})