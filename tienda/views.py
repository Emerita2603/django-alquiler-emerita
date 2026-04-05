import csv
import datetime
import io
import random

from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Count, F, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import (
    AlquilerCreateForm,
    ImportarClientesCSVForm,
    MarcarPagadoForm,
    PeliculaForm,
    SimularVentasForm,
)
from .mixins import VistaConPermisoMixin, VistaPrivadaMixin
from .models import Alquiler, Categoria, Cliente, Pelicula


def index(request: HttpRequest) -> HttpResponse:
    total_peliculas = Pelicula.objects.count()
    total_clientes = Cliente.objects.count()
    alquileres_pendientes = Alquiler.objects.filter(estado="pendiente").count()
    ingresos = (
        Alquiler.objects.filter(estado="pagado")
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

    def get_queryset(self):
        return super().get_queryset().prefetch_related("peliculas")


class CategoriaCreateView(VistaConPermisoMixin, CreateView):
    permission_required = "tienda.add_categoria"
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaUpdateView(VistaConPermisoMixin, UpdateView):
    permission_required = "tienda.change_categoria"
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaDeleteView(VistaConPermisoMixin, DeleteView):
    permission_required = "tienda.delete_categoria"
    model = Categoria
    template_name = "tienda/categoria_confirm_delete.html"
    success_url = reverse_lazy("categoria_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "No puedes eliminar esta categoría porque tiene películas asociadas.")
            return redirect("categoria_list")


class ClienteListView(VistaPrivadaMixin, ListView):
    model = Cliente
    template_name = "tienda/cliente_list.html"
    context_object_name = "clientes"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("alquileres")


class ClienteCreateView(VistaConPermisoMixin, CreateView):
    permission_required = "tienda.add_cliente"
    model = Cliente
    fields = ["dni", "nombre", "email", "telefono"]
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


class ClienteUpdateView(VistaConPermisoMixin, UpdateView):
    permission_required = "tienda.change_cliente"
    model = Cliente
    fields = ["dni", "nombre", "email", "telefono"]
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


class ClienteDeleteView(VistaConPermisoMixin, DeleteView):
    permission_required = "tienda.delete_cliente"
    model = Cliente
    template_name = "tienda/cliente_confirm_delete.html"
    success_url = reverse_lazy("cliente_list")


class ClientesSinAlquilerView(VistaPrivadaMixin, ListView):
    model = Cliente
    template_name = "tienda/clientes_sin_alquiler.html"
    context_object_name = "clientes"

    def get_queryset(self):
        return (
            Cliente.objects
            .annotate(total_alquileres=Count("alquileres"))
            .filter(total_alquileres=0)
            .order_by("nombre")
        )    

class TicketPromedioView(VistaPrivadaMixin, View):
    template_name = "tienda/ticket_promedio.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        promedio = (
            Alquiler.objects
            .filter(estado="pagado")
            .aggregate(ticket_promedio=Avg("precio"))
            .get("ticket_promedio")
        )

        return render(
            request,
            self.template_name,
            {"promedio": promedio},
        )

class RankingClientesMensualView(VistaPrivadaMixin, View):
    template_name = "tienda/ranking_clientes_mensual.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()

        try:
            mes = int(request.GET.get("mes", hoy.month))
        except (TypeError, ValueError):
            mes = hoy.month

        try:
            anio = int(request.GET.get("anio", hoy.year))
        except (TypeError, ValueError):
            anio = hoy.year

        datos = (
            Alquiler.objects
            .filter(
                estado="pagado",
                fecha_alquiler__month=mes,
                fecha_alquiler__year=anio,
            )
            .values("cliente__id", "cliente__nombre", "cliente__dni")
            .annotate(total_gastado=Sum("precio"))
            .order_by("-total_gastado", "cliente__nombre")
        )

        return render(
            request,
            self.template_name,
            {
                "datos": datos,
                "mes": mes,
                "anio": anio,
            },
        )

class VentasPorDiaView(VistaPrivadaMixin, View):
    template_name = "tienda/ventas_por_dia.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        hoy = timezone.localdate()

        desde_str = request.GET.get("desde")
        hasta_str = request.GET.get("hasta")

        try:
            desde = datetime.datetime.strptime(desde_str, "%Y-%m-%d").date() if desde_str else hoy
        except ValueError:
            desde = hoy

        try:
            hasta = datetime.datetime.strptime(hasta_str, "%Y-%m-%d").date() if hasta_str else hoy
        except ValueError:
            hasta = hoy

        if desde > hasta:
            desde, hasta = hasta, desde

        datos = (
            Alquiler.objects
            .filter(
                estado="pagado",
                fecha_alquiler__gte=desde,
                fecha_alquiler__lte=hasta,
            )
            .values("fecha_alquiler")
            .annotate(total_ventas=Sum("precio"))
            .order_by("fecha_alquiler")
        )

        total_general = (
            Alquiler.objects
            .filter(
                estado="pagado",
                fecha_alquiler__gte=desde,
                fecha_alquiler__lte=hasta,
            )
            .aggregate(total=Sum("precio"))
            .get("total")
            or 0
        )

        return render(
            request,
            self.template_name,
            {
                "datos": datos,
                "desde": desde,
                "hasta": hasta,
                "total_general": total_general,
            },
        )

class AlquileresVencidosView(VistaPrivadaMixin, ListView):
    model = Alquiler
    template_name = "tienda/alquileres_vencidos.html"
    context_object_name = "alquileres"

    def get_queryset(self):
        return (
            Alquiler.objects
            .filter(estado="pendiente", fecha_alquiler__lt=timezone.localdate())
            .select_related("cliente", "pelicula", "pelicula__categoria")
            .order_by("fecha_alquiler")
        )

class ImportarClientesCSVView(VistaConPermisoMixin, View):
    permission_required = "tienda.add_cliente"
    template_name = "tienda/importar_clientes.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ImportarClientesCSVForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ImportarClientesCSVForm(request.POST, request.FILES)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        archivo = form.cleaned_data["archivo"]

        try:
            contenido = archivo.read().decode("utf-8")
        except UnicodeDecodeError:
            form.add_error("archivo", "El archivo debe estar codificado en UTF-8.")
            return render(request, self.template_name, {"form": form})

        reader = csv.DictReader(io.StringIO(contenido))

        columnas_esperadas = {"nombre", "email", "telefono"}
        if not reader.fieldnames:
            form.add_error("archivo", "El CSV está vacío o no tiene encabezados.")
            return render(request, self.template_name, {"form": form})

        encabezados = {h.strip().lower() for h in reader.fieldnames if h}
        if not columnas_esperadas.issubset(encabezados):
            form.add_error(
                "archivo",
                "El CSV debe contener las columnas: nombre, email, telefono.",
            )
            return render(request, self.template_name, {"form": form})

        creados = 0
        errores = []

        for numero_fila, fila in enumerate(reader, start=2):
            nombre = (fila.get("nombre") or "").strip()
            email = (fila.get("email") or "").strip()
            telefono = (fila.get("telefono") or "").strip()

            if not nombre and not email and not telefono:
                continue

            if not nombre:
                errores.append(f"Fila {numero_fila}: nombre vacío.")
                continue

            if not email:
                errores.append(f"Fila {numero_fila}: email vacío.")
                continue

            if Cliente.objects.filter(email=email).exists():
                errores.append(f"Fila {numero_fila}: el email '{email}' ya existe.")
                continue

            cliente = Cliente(nombre=nombre, email=email, telefono=telefono)

            try:
                cliente.full_clean()
                cliente.save()
                creados += 1
            except Exception as e:
                errores.append(f"Fila {numero_fila}: {e}")

        if creados:
            messages.success(request, f"Se importaron {creados} cliente(s) correctamente.")

        if errores:
            messages.warning(request, "Algunas filas no se importaron.")
            return render(
                request,
                self.template_name,
                {
                    "form": ImportarClientesCSVForm(),
                    "errores": errores,
                    "creados": creados,
                },
            )

        return redirect("cliente_list")


class PeliculaListView(VistaPrivadaMixin, ListView):
    model = Pelicula
    template_name = "tienda/pelicula_list.html"
    context_object_name = "peliculas"

    def get_queryset(self):
        qs = super().get_queryset().select_related("categoria").prefetch_related("alquileres")

        anio = self.request.GET.get("anio")
        categoria = self.request.GET.get("categoria")
        precio_min = self.request.GET.get("precio_min")
        precio_max = self.request.GET.get("precio_max")

        if anio:
            qs = qs.filter(anio=anio)

        if categoria:
            qs = qs.filter(categoria_id=categoria)

        if precio_min:
            qs = qs.filter(precio_alquiler__gte=precio_min)

        if precio_max:
            qs = qs.filter(precio_alquiler__lte=precio_max)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = Categoria.objects.all().order_by("nombre")
        ctx["filtro_anio"] = self.request.GET.get("anio", "")
        ctx["filtro_categoria"] = self.request.GET.get("categoria", "")
        ctx["filtro_precio_min"] = self.request.GET.get("precio_min", "")
        ctx["filtro_precio_max"] = self.request.GET.get("precio_max", "")
        return ctx


class TopPeliculasView(VistaPrivadaMixin, ListView):
    model = Pelicula
    template_name = "tienda/top_peliculas.html"
    context_object_name = "peliculas"

    def get_queryset(self):
        return (
            Pelicula.objects
            .annotate(total_alquileres=Count("alquileres"))
            .order_by("-total_alquileres", "titulo")[:10]
        )


class IngresosPorCategoriaView(VistaPrivadaMixin, View):
    template_name = "tienda/ingresos_por_categoria.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        datos = (
            Alquiler.objects
            .filter(estado="pagado")
            .values("pelicula__categoria__nombre")
            .annotate(total_ingresos=Sum("precio"))
            .order_by("-total_ingresos")
        )

        return render(
            request,
            self.template_name,
            {"datos": datos},
        )

class PeliculaCreateView(VistaConPermisoMixin, CreateView):
    permission_required = "tienda.add_pelicula"
    model = Pelicula
    form_class = PeliculaForm
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaUpdateView(VistaConPermisoMixin, UpdateView):
    permission_required = "tienda.change_pelicula"
    model = Pelicula
    form_class = PeliculaForm
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaDeleteView(VistaConPermisoMixin, DeleteView):
    permission_required = "tienda.delete_pelicula"
    model = Pelicula
    template_name = "tienda/pelicula_confirm_delete.html"
    success_url = reverse_lazy("pelicula_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "No puedes eliminar esta película porque tiene alquileres asociados.")
            return redirect("pelicula_list")


class AlquilerCreateView(VistaConPermisoMixin, CreateView):
    permission_required = "tienda.add_alquiler"
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
        estado = self.request.GET.get("estado")
        if estado in ["pendiente", "pagado", "anulado"]:
            qs = qs.filter(estado=estado)
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
            alquiler.marcar_pagado(
                 fecha_devolucion=form.cleaned_data.get("fecha_devolucion")
            )

            alquiler.metodo_pago = form.cleaned_data.get("metodo_pago")
            alquiler.save(update_fields=["metodo_pago"])

            messages.success(request, "El alquiler fue marcado como pagado correctamente.")
            next_url = request.GET.get("next")
            return redirect(next_url or "alquiler_list")

        return render(request, self.template_name, {"alquiler": alquiler, "form": form})


class VentasListView(VistaPrivadaMixin, ListView):
    model = Alquiler
    template_name = "tienda/ventas_list.html"
    context_object_name = "ventas"

    def get_queryset(self):
        return (
            Alquiler.objects.filter(estado="pagado")
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
                    estado="pagado",
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

    