from flask import Flask
from models import Base
from dbConnect import engine
app = Flask(__name__)

Base.metadata.create_all(engine)

if __name__ == "__main__":
    app.run(host='localhost', port=8000)
