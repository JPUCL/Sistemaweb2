import os
from typing import Optional

USAR_TINYDB = os.getenv('USE_TINYDB', 'false').lower() == 'true'

if USAR_TINYDB:
    from tiny_store import (
        init_tinydb,
        criar_entregador_td,
        obter_entregador_por_nome_td,
        listar_entregadores_td,
        criar_entrega_td,
        listar_entregas_td,
        atribuir_entrega_td,
        atualizar_status_entrega_td,
        obter_entrega_td,
        enviar_mensagem_td,
        receber_mensagem_td,
        deletar_mensagem_td,
    )
else:
    from models import db, Entregador as Driver, Entrega as Delivery


def iniciar_armazenamento(app):
    if USAR_TINYDB:
        init_tinydb()
    else:
        db.init_app(app)

# Drivers
def criar_entregador(name, phone, password_hash):
    if USAR_TINYDB:
        return criar_entregador_td(name, phone, password_hash)
    d = Driver(name=name, phone=phone, password_hash=password_hash)
    db.session.add(d)
    db.session.commit()
    return {'id': d.id, 'name': d.name, 'phone': d.phone, 'password_hash': d.password_hash}

def obter_entregador_por_nome(name):
    if USAR_TINYDB:
        return obter_entregador_por_nome_td(name)
    d = Driver.query.filter_by(name=name).first()
    if not d:
        return None
    return {'id': d.id, 'name': d.name, 'phone': d.phone, 'password_hash': d.password_hash}

def listar_entregadores():
    if USAR_TINYDB:
        return listar_entregadores_td()
    items = Driver.query.order_by(Driver.created_at.desc()).all()
    out = []
    for d in items:
        out.append({'id': d.id, 'name': d.name, 'phone': d.phone, 'password_hash': d.password_hash})
    return out

# Deliveries
def criar_entrega(restaurant, pickup_address, customer_address, status='enfileirado'):
    if USAR_TINYDB:
        return criar_entrega_td(restaurant, pickup_address, customer_address, status)
    o = Delivery(restaurant=restaurant, pickup_address=pickup_address, customer_address=customer_address, status=status)
    db.session.add(o)
    db.session.commit()
    return {'id': o.id, 'restaurante': o.restaurant, 'endereco_retirada': o.pickup_address, 'endereco_cliente': o.customer_address, 'status': o.status, 'id_entregador': o.assigned_driver_id}

def listar_entregas():
    if USAR_TINYDB:
        return listar_entregas_td()
    items = Delivery.query.order_by(Delivery.created_at.desc()).all()
    out = []
    for o in items:
        out.append({'id': o.id, 'restaurante': o.restaurant, 'endereco_retirada': o.pickup_address, 'endereco_cliente': o.customer_address, 'status': o.status, 'id_entregador': o.assigned_driver_id})
    return out

def obter_entrega(delivery_id):
    if USAR_TINYDB:
        return obter_entrega_td(delivery_id)
    o = Delivery.query.get(delivery_id)
    if not o:
        return None
    return {'id': o.id, 'restaurante': o.restaurant, 'endereco_retirada': o.pickup_address, 'endereco_cliente': o.customer_address, 'status': o.status, 'id_entregador': o.assigned_driver_id}

def atribuir_entrega(delivery_id, driver_id, status='atribuido'):
    if USAR_TINYDB:
        return atribuir_entrega_td(delivery_id, driver_id, status)
    o = Delivery.query.get(delivery_id)
    if not o:
        return None
    o.assigned_driver_id = driver_id
    o.status = status
    db.session.commit()
    return {'id': o.id, 'restaurante': o.restaurant, 'endereco_retirada': o.pickup_address, 'endereco_cliente': o.customer_address, 'status': o.status, 'id_entregador': o.assigned_driver_id}

def atualizar_status_entrega(delivery_id, status):
    if USAR_TINYDB:
        return atualizar_status_entrega_td(delivery_id, status)
    o = Delivery.query.get(delivery_id)
    if not o:
        return None
    o.status = status
    db.session.commit()
    return {'id': o.id, 'status': o.status}

# Queue wrappers for tinydb (if used)
def enviar_mensagem_fila(delivery_id):
    if USAR_TINYDB:
        return enviar_mensagem_td(delivery_id)
    raise RuntimeError('enviar_mensagem_fila: apenas suportado quando USE_TINYDB=true')

def receber_mensagem_fila():
    if USAR_TINYDB:
        return receber_mensagem_td()
    raise RuntimeError('receber_mensagem_fila: apenas suportado quando USE_TINYDB=true')

def deletar_mensagem_fila(receipt_handle):
    """Apaga mensagem da fila (apenas TinyDB suportado nesta camada).

    Para SQS use o adaptador em `queue.py` que expõe `delete_message`.
    """
    if USAR_TINYDB:
        return deletar_mensagem_td(receipt_handle)
    raise RuntimeError('deletar_mensagem_fila: apenas suportado quando USE_TINYDB=true')

def criar_tabelas():
    """Cria as tabelas quando usando SQLAlchemy. No-op para TinyDB."""
    if not USAR_TINYDB:
        db.create_all()
 