from __future__ import annotations

import datetime

from django import forms

from .models import Alquiler, Categoria, Cliente, Pelicula
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
        fields = ["nombre", "email", "telefono"]


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

        pendientes = Alquiler.objects.filter(cliente=cliente, pagado=False).count()
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