#!/usr/bin/env python
"""Entrada administrativa da aplicação Django do ContaView."""

import os
import sys


def principal() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "configuracao.settings.desenvolvimento"
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as erro:
        raise ImportError(
            "Django não está instalado. Execute a instalação das dependências."
        ) from erro
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    principal()
