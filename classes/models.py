from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(100), nullable=False)
    pregunta = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    evaluacion = db.Column(db.String(10), nullable=False)  # "up" o "down"
    motivo = db.Column(db.Text, nullable=True)  # Razón para thumbs-down

    def __repr__(self):
        return f"<Feedback {self.id}>"