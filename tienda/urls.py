from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # Categorias
    path("categorias/", views.CategoriaListView.as_view(), name="categoria_list"),
    path("categorias/nueva/", views.CategoriaCreateView.as_view(), name="categoria_create"),
    path("categorias/<int:pk>/editar/", views.CategoriaUpdateView.as_view(), name="categoria_update"),
    path("categorias/<int:pk>/eliminar/", views.CategoriaDeleteView.as_view(), name="categoria_delete"),
    # Peliculas
    path("peliculas/", views.PeliculaListView.as_view(), name="pelicula_list"),
    path("peliculas/nueva/", views.PeliculaCreateView.as_view(), name="pelicula_create"),
    path("peliculas/<int:pk>/editar/", views.PeliculaUpdateView.as_view(), name="pelicula_update"),
    path("peliculas/<int:pk>/eliminar/", views.PeliculaDeleteView.as_view(), name="pelicula_delete"),
    # Clientes
    path("clientes/", views.ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", views.ClienteCreateView.as_view(), name="cliente_create"),
    path("clientes/<int:pk>/editar/", views.ClienteUpdateView.as_view(), name="cliente_update"),
    path("clientes/<int:pk>/eliminar/", views.ClienteDeleteView.as_view(), name="cliente_delete"),
    path("clientes/importar/", views.ImportarClientesCSVView.as_view(), name="cliente_importar"),
    # Alquileres
    path("alquileres/", views.AlquilerListView.as_view(), name="alquiler_list"),
    path("alquileres/nuevo/", views.AlquilerCreateView.as_view(), name="alquiler_create"),
    path("alquileres/<int:pk>/marcar-pagado/", views.MarcarPagadoView.as_view(), name="alquiler_marcar_pagado"),
    path("reportes/top-peliculas/", views.TopPeliculasView.as_view(), name="top_peliculas"),
    path("reportes/ingresos-por-categoria/", views.IngresosPorCategoriaView.as_view(), name="ingresos_por_categoria"),    
    # Ventas (en esta versión: alquileres pagados)
    path("ventas/", views.VentasListView.as_view(), name="ventas_list"),
    path("ventas/simular/", views.simular_ventas, name="ventas_simular"),
]

