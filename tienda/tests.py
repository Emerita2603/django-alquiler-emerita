import os
import json
from django.core.management import call_command
import datetime
from decimal import Decimal
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import (
    AlquilerCreateForm,
    ImportarClientesCSVForm,
    PeliculaForm,
    SimularVentasForm,
)
from .models import Alquiler, Categoria, Cliente, Pelicula


class PeliculaFormTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Acción",
            descripcion="Películas de acción",
        )

    def test_pelicula_form_valido(self):
        form = PeliculaForm(
            data={
                "titulo": "Matrix",
                "slug": "emerit-97-matrix",
                "descripcion": "Película de ciencia ficción",
                "anio": 1999,
                "categoria": self.categoria.id,
                "precio_alquiler": "10.00",
                "stock": 2,
            }
        )
        self.assertTrue(form.is_valid())

    def test_pelicula_form_slug_invalido(self):
        form = PeliculaForm(
            data={
                "titulo": "Matrix",
                "slug": "matrix",
                "descripcion": "Película de ciencia ficción",
                "anio": 1999,
                "categoria": self.categoria.id,
                "precio_alquiler": "10.00",
                "stock": 2,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("slug", form.errors)

    def test_pelicula_form_precio_menor_al_minimo(self):
        form = PeliculaForm(
            data={
                "titulo": "Matrix",
                "slug": "emerit-97-matrix",
                "descripcion": "Película de ciencia ficción",
                "anio": 1999,
                "categoria": self.categoria.id,
                "precio_alquiler": "2.00",
                "stock": 2,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("precio_alquiler", form.errors)


class AlquilerCreateFormTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Drama",
            descripcion="Películas dramáticas",
        )
        self.cliente = Cliente.objects.create(
            nombre="Juan Pérez",
            email="juan@test.com",
            telefono="999111222",
        )
        self.pelicula_valida = Pelicula.objects.create(
            titulo="Titanic",
            slug="emerit-97-titanic",
            descripcion="Drama romántico",
            anio=1997,
            categoria=self.categoria,
            precio_alquiler=Decimal("10.00"),
            stock=2,
        )
        self.pelicula_sin_stock = Pelicula.objects.create(
            titulo="Avatar",
            slug="emerit-97-avatar",
            descripcion="Ciencia ficción",
            anio=2009,
            categoria=self.categoria,
            precio_alquiler=Decimal("12.00"),
            stock=1,
        )

    def test_alquiler_form_valido(self):
        form = AlquilerCreateForm(
            data={
                "cliente": self.cliente.id,
                "pelicula": self.pelicula_valida.id,
            }
        )
        self.assertTrue(form.is_valid())

    def test_alquiler_form_invalido_por_stock(self):
        form = AlquilerCreateForm(
            data={
                "cliente": self.cliente.id,
                "pelicula": self.pelicula_sin_stock.id,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_alquiler_form_invalido_por_limite_pendientes(self):
        for i in range(4):
            pelicula = Pelicula.objects.create(
                titulo=f"Peli {i}",
                slug=f"emerit-97-peli-{i}",
                descripcion="Prueba",
                anio=2000 + i,
                categoria=self.categoria,
                precio_alquiler=Decimal("10.00"),
                stock=2,
            )
            Alquiler.objects.create(
                cliente=self.cliente,
                pelicula=pelicula,
                pagado=False,
            )

        nueva_pelicula = Pelicula.objects.create(
            titulo="Nueva",
            slug="emerit-97-nueva",
            descripcion="Prueba",
            anio=2024,
            categoria=self.categoria,
            precio_alquiler=Decimal("10.00"),
            stock=2,
        )

        form = AlquilerCreateForm(
            data={
                "cliente": self.cliente.id,
                "pelicula": nueva_pelicula.id,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)


class ImportarClientesCSVFormTest(TestCase):
    def test_csv_form_valido(self):
        archivo = SimpleUploadedFile(
            "clientes.csv",
            b"nombre,email,telefono\nJuan,juan@test.com,999111222\n",
            content_type="text/csv",
        )
        form = ImportarClientesCSVForm(files={"archivo": archivo})
        self.assertTrue(form.is_valid())

    def test_csv_form_invalido_por_extension(self):
        archivo = SimpleUploadedFile(
            "clientes.txt",
            b"nombre,email,telefono\nJuan,juan@test.com,999111222\n",
            content_type="text/plain",
        )
        form = ImportarClientesCSVForm(files={"archivo": archivo})
        self.assertFalse(form.is_valid())
        self.assertIn("archivo", form.errors)


class SimularVentasFormTest(TestCase):
    def test_simular_ventas_form_valido(self):
        form = SimularVentasForm(
            data={
                "numero_ventas": 10,
                "desde": "2026-01-01",
                "hasta": "2026-01-10",
            }
        )
        self.assertTrue(form.is_valid())

    def test_simular_ventas_form_invalido_por_rango(self):
        form = SimularVentasForm(
            data={
                "numero_ventas": 10,
                "desde": "2026-01-10",
                "hasta": "2026-01-01",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_simular_ventas_form_completa_fechas_si_van_vacias(self):
        form = SimularVentasForm(
            data={
                "numero_ventas": 5,
                "desde": "",
                "hasta": "",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.cleaned_data["desde"])
        self.assertIsNotNone(form.cleaned_data["hasta"])

class ComandoGenerarRetoTest(TestCase):
    def test_generar_reto_personalizado(self):
        alumno = "Test Alumno"
        codigo = "TEST123"

        # Ejecutar comando
        call_command(
            "generar_reto_personalizado",
            alumno=alumno,
            codigo=codigo,
        )

        # Nombre esperado del archivo
        archivo = f"retos/test-alumno-{codigo.lower()}.json"

        # Verificar que existe
        self.assertTrue(os.path.exists(archivo))

        # Leer contenido
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validaciones
        self.assertEqual(data["alumno"], alumno)
        self.assertEqual(data["codigo"], codigo)
        self.assertIn("token_entrega", data)

        # Limpieza (opcional)
        os.remove(archivo)        