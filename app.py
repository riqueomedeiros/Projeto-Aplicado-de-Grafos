"""Ponto de entrada do servidor Flask de desenvolvimento."""

from hospitalflow.web import criar_app

app = criar_app()

if __name__ == "__main__":
    app.run()
