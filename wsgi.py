from app.api import flask_app as application

if __name__ == "__main__":
    application.run(debug=True, host='0.0.0.0')
