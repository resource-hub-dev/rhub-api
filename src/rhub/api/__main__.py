from . import create_app, init_app


app = create_app()

with app.app_context():
    init_app()

app.run(port=8081)
