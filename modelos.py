from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Entregador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant = db.Column(db.String(200), nullable=False)
    pickup_address = db.Column(db.String(300), nullable=False)
    customer_address = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(50), default='enfileirado')
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey('entregador.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MensagemFila(db.Model):
    """Tabela de fila persistente simples que armazena IDs de entregas em ordem FIFO.
    Este modelo era usado para simular uma fila SQS em cenários de demonstração.
    """
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('entrega.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

