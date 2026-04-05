from __future__ import annotations

import datetime

from django import forms

from .models import Alquiler, Categoria, Cliente, MetodoPago, Pelicula
from django.conf import settings

STOCK_MINIMO_PELICULA = 2
LIMITE_ALQUILERES_PENDIENTES = 4


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["dni", "nombre", "email", "telefono"]


from django import forms
from django.conf import settings
from django.utils import timezone
from .models import Pelicula


class PeliculaForm(forms.ModelForm):
    class Meta:
        model = Pelicula
        fields = ["titulo", "slug", "descripcion", "anio", "categoria", "precio_alquiler", "stock"]

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        if slug and not slug.startswith("emerit-97"):
            raise forms.ValidationError("El slug debe comenzar con el prefijo obligatorio 'emerit-97'.")
        return slug

    def clean_precio_alquiler(self):
        precio = self.cleaned_data["precio_alquiler"]
        if precio < settings.PRECIO_MINIMO_PELICULA:
            raise forms.ValidationError(
                f"El precio no puede ser menor a {settings.PRECIO_MINIMO_PELICULA} soles."
            )
        return precio

    def clean_anio(self):
        anio = self.cleaned_data["anio"]
        anio_actual = timezone.localdate().year

        if anio > anio_actual:
            raise forms.ValidationError("El año no puede ser mayor al actual.")

        return anio    


class AlquilerCreateForm(forms.ModelForm):
    class Meta:
        model = Alquiler
        fields = ["cliente", "pelicula"]

    def clean(self):
        cleaned = super().clean()
        cliente = cleaned.get("cliente")
        pelicula = cleaned.get("pelicula")

        if not cliente or not pelicula:
            return cleaned

        if pelicula.stock < STOCK_MINIMO_PELICULA:
            raise forms.ValidationError(
                f"No se puede alquilar esta película porque el stock debe ser al menos {STOCK_MINIMO_PELICULA}."
            )

        pendientes = Alquiler.objects.filter(cliente=cliente, estado="pendiente").count()
        if pendientes >= LIMITE_ALQUILERES_PENDIENTES:
            raise forms.ValidationError(
                f"El cliente ya alcanzó el límite de {LIMITE_ALQUILERES_PENDIENTES} alquileres pendientes."
            )

        return cleaned


class MarcarPagadoForm(forms.Form):
    fecha_devolucion = forms.DateField(
        required=False,
        label="Fecha de devolución (opcional)",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    metodo_pago = forms.ModelChoiceField(
        queryset=MetodoPago.objects.all(),
        required=True,
        label="Método de pago",
    )


class SimularVentasForm(forms.Form):
    numero_ventas = forms.IntegerField(min_value=1, max_value=200, label="Cantidad de ventas a simular")
    desde = forms.DateField(required=False, label="Desde (opcional)", widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, label="Hasta (opcional)", widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned = super().clean()
        desde = cleaned.get("desde")
        hasta = cleaned.get("hasta")

        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha 'Desde' no puede ser posterior a 'Hasta'.")

        if not desde and not hasta:
            today = datetime.date.today()
            cleaned["desde"] = today
            cleaned["hasta"] = today

        return cleaned

class ImportarClientesCSVForm(forms.Form):
    archivo = forms.FileField(label="Archivo CSV")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".csv"):
            raise forms.ValidationError("Debes subir un archivo CSV.")
        return archivo