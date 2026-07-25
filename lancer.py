"""Point d'entrée du bundle PyInstaller.

PyInstaller a besoin d'un script de premier niveau situé hors du paquet ;
``tpt_app.main`` reste utilisable directement via ``python -m tpt_app.main``.
"""

from tpt_app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
