from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """
    Paginación por defecto del API.

    Igual que PageNumberPagination pero honra `?page_size=N` del cliente
    (acotado a `max_page_size`). El panel admin lo usa para traer un mes
    completo en 1-2 requests en vez de encadenar decenas de páginas de 20.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
