from django.contrib import admin

from .models import Alquiler, Categoria, Cliente, MetodoPago, Pelicula


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("dni", "nombre", "email", "telefono")
    search_fields = ("dni", "nombre", "email")


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "director", "pais_origen", "duracion_minutos", "anio", "categoria", "precio_alquiler", "stock")
    list_filter = ("categoria", "anio")
    search_fields = ("titulo", "slug")


@admin.register(Alquiler)
class AlquilerAdmin(admin.ModelAdmin):
    list_display = ("fecha_alquiler", "cliente", "pelicula", "metodo_pago", "estado", "precio", "fecha_devolucion")
    list_filter = ("estado", "fecha_alquiler", "fecha_devolucion", "metodo_pago")
    search_fields = ("cliente__nombre", "pelicula__titulo")