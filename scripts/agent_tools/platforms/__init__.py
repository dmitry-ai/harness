"""Native boundaries; core workflow routes saved evidence by its actual surface."""

from importlib import import_module
from ..runtime import platform_name, settings


def adapter(platform=None, surface=None):
    if surface:
        matches = [name for name, value in settings()['platforms'].items() if value['surface'] == surface]
        if len(matches) != 1:
            raise ValueError('Unsupported native evidence surface')
        platform = matches[0]
    return import_module('.' + platform_name(platform), __name__)
