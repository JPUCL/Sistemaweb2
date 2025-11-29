from tinydb import TinyDB, Query
from datetime import datetime
import os
import threading

_db = None
_db_lock = threading.Lock()

def init_tinydb(path=None):
    global _db
    with _db_lock:
        if _db is None:
            path = path or os.getenv('TINYDB_PATH', 'tinydb.json')
            _db = TinyDB(path)
    return _db

# Drivers
def criar_entregador_td(name, phone, password_hash):
    db = init_tinydb()
    drivers = db.table('drivers')
    doc = {'name': name, 'phone': phone, 'password_hash': password_hash, 'created_at': datetime.utcnow().isoformat()}
    doc_id = drivers.insert(doc)
    doc['id'] = doc_id
    return doc

def obter_entregador_por_nome_td(name):
    db = init_tinydb()
    drivers = db.table('drivers')
    Driver = Query()
    res = drivers.get(Driver.name == name)
    if not res:
        return None
    res['id'] = res.doc_id
    return res

def listar_entregadores_td():
    db = init_tinydb()
    drivers = db.table('drivers')
    res = []
    # retornar em ordem decrescente de criação
    for item in drivers.all()[::-1]:
        item['id'] = item.doc_id
        res.append(item)
    return res

# Deliveries
def criar_entrega_td(restaurant, pickup_address, customer_address, status='enfileirado'):
    db = init_tinydb()
    deliveries = db.table('deliveries')
    doc = {'restaurante': restaurant, 'endereco_retirada': pickup_address, 'endereco_cliente': customer_address, 'status': status, 'id_entregador': None, 'created_at': datetime.utcnow().isoformat()}
    doc_id = deliveries.insert(doc)
    doc['id'] = doc_id
    return doc

def listar_entregas_td():
    db = init_tinydb()
    deliveries = db.table('deliveries')
    res = []
    for item in deliveries.all()[::-1]:
        item['id'] = item.doc_id
        res.append(item)
    return res

def obter_entrega_td(delivery_id):
    db = init_tinydb()
    deliveries = db.table('deliveries')
    res = deliveries.get(doc_id=int(delivery_id))
    if not res:
        return None
    res['id'] = res.doc_id
    return res

def atribuir_entrega_td(delivery_id, driver_id, status='atribuido'):
    db = init_tinydb()
    deliveries = db.table('deliveries')
    deliveries.update({'assigned_driver_id': int(driver_id), 'status': status}, doc_ids=[int(delivery_id)])
    return obter_entrega_td(delivery_id)

def atualizar_status_entrega_td(delivery_id, status):
    db = init_tinydb()
    deliveries = db.table('deliveries')
    deliveries.update({'status': status}, doc_ids=[int(delivery_id)])
    return obter_entrega_td(delivery_id)

# Fila usando TinyDB (FIFO simples)
def enviar_mensagem_td(delivery_id):
    db = init_tinydb()
    queue = db.table('queue')
    doc = {'id_entrega': int(delivery_id), 'created_at': datetime.utcnow().isoformat()}
    doc_id = queue.insert(doc)
    return {'MessageId': doc_id}

def receber_mensagem_td():
    db = init_tinydb()
    queue = db.table('queue')
    all_msgs = queue.all()
    if not all_msgs:
        return None
    # FIFO: take the first inserted
    first = all_msgs[0]
    msg_id = first.doc_id
    delivery_id = first.get('id_entrega')
    # NOTA: não deletar imediatamente — retornar ReceiptHandle para permitir ack/delete explícito
    delivery = obter_entrega_td(delivery_id)
    return {'MessageId': msg_id, 'ReceiptHandle': msg_id, 'entrega': delivery}


def deletar_mensagem_td(receipt_handle):
    db = init_tinydb()
    queue = db.table('queue')
    try:
        queue.remove(doc_ids=[int(receipt_handle)])
        return True
    except Exception:
        return False
 