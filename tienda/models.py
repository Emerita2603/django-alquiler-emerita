from decimal import Decimal

from django.core.validators import MinLengthValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Cliente(models.Model):
    dni = models.CharField(
    max_length=8,
    unique=True,
    validators=[
        MinLengthValidator(8),
        RegexValidator(
            regex=r"^\d{8}$",
            message="El DNI debe tener exactamente 8 dígitos numéricos.",
        ),
    ],
)
    nombre = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True, unique=True)
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} - {self.dni}"


class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre

class Pelicula(models.Model):
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Duración de la película en minutos.",
    )
    anio = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)],
        verbose_name="Año",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="peliculas",
    )
    precio_alquiler = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    stock = models.PositiveIntegerField(default=2)

    class Meta:
        ordering = ["titulo", "anio"]
        unique_together = [("titulo", "anio")]

    def __str__(self) -> str:
        return f"{self.titulo} ({self.anio})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            self.slug = f"emerit-97-{base_slug}"
        super().save(*args, **kwargs)


class Alquiler(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="alquileres")
    pelicula = models.ForeignKey(Pelicula, on_delete=models.PROTECT, related_name="alquileres")
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alquileres",
    )

    fecha_alquiler = models.DateField(default=timezone.localdate)
    fecha_devolucion = models.DateField(blank=True, null=True)
    fecha_pago = models.DateField(blank=True, null=True)

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
        ("anulado", "Anulado"),
    ]

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="pendiente",
    )

    precio = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["-fecha_alquiler", "-id"]

    def __str__(self) -> str:
        return f"Alquiler: {self.pelicula} - {self.cliente}"

    def marcar_pagado(self, fecha_devolucion=None) -> None:
        if fecha_devolucion is None:
            fecha_devolucion = timezone.localdate()

        self.estado = "pagado"
        self.fecha_devolucion = fecha_devolucion
        self.fecha_pago = timezone.localdate()
        self.save(update_fields=["estado", "fecha_devolucion", "fecha_pago"])

    def calcular_mora(self):
        if not self.fecha_devolucion:
            return 0

        dias_retraso = (self.fecha_devolucion - self.fecha_alquiler).days

        if dias_retraso <= 0:
            return 0

        dias_cobrables = min(dias_retraso, 9)
        return dias_cobrables * 5

    def save(self, *args, **kwargs):
        if self.precio is None:
            self.precio = self.pelicula.precio_alquiler
        super().save(*args, **kwargs)