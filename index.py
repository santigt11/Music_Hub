from app import app

# Handler para Vercel
def handler(request):
    return app

# También exportar como application
application = app

if __name__ == "__main__":
    app.run()