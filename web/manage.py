#!/usr/bin/env python
"""Entrada administrativa da aplicação Django do ContaView."""

import os
import sys
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))


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
