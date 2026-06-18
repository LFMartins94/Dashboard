import os

import reflex as rx

config = rx.Config(
    app_name="contaview",
    db_url=os.getenv("DATABASE_URL"),
)
