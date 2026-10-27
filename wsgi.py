import app as application

if __name__ == "__main__":
    from waitress import serve
    print("Starting production WSGI server on http://127.0.0.1:5000")
    serve(application.app, host="127.0.0.1", port=5000, threads=8)