"""File-based incremental CDR catalogs."""
from .files import FileCatalog

Catalog = FileCatalog
__all__ = ['Catalog', 'FileCatalog']
