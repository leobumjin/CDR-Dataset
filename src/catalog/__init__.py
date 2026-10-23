"""Semantic feature catalogs, independent of sample source runs."""
from .files import FileCatalog

Catalog = FileCatalog
__all__ = ['Catalog', 'FileCatalog']
