import os
import time


def main():
    # forçar TinyDB mode
    os.environ['USE_TINYDB'] = 'true'

    # importar aqui depois de setar var de ambiente
    from app import create_app
    from queue import get_queue
    from storage import listar_entregadores, atribuir_entrega, obter_entrega
    import worker as worker_mod

    app = create_app()

    client = app.test_client()

    # 1) criar entregador
    resp = client.post('/drivers/register', json={'nome': 'Joao', 'senha': 'secret'})
    print('register status:', resp.status_code, resp.get_json())
    assert resp.status_code == 201
    driver = resp.get_json()
    driver_id = driver.get('id')

    # 2) criar pedido
    order_payload = {'restaurante': 'Pizzaria', 'endereco_retirada': 'Rua A, 10', 'endereco_cliente': 'Rua B, 20'}
    resp = client.post('/orders', json=order_payload)
    print('create order status:', resp.status_code, resp.get_json())
    assert resp.status_code == 201
    order = resp.get_json()
    order_id = order.get('id')

    # 3) pegar mensagem da fila (TinyDB queue)
    q = get_queue()
    msg = q.receive_message()
    print('fila recebeu:', msg)
    assert msg is not None, 'mensagem não encontrada na fila'

    receipt = msg.get('ReceiptHandle') or msg.get('receipt')
    entrega = msg.get('entrega') or msg.get('delivery')
    assert entrega is not None
    delivery_id = entrega.get('id')

    # 4) selecionar entregador (usar helper do worker) e atribuir
    drivers = listar_entregadores()
    picked = worker_mod.selecionar_entregador_round_robin(drivers, {'last_index': 0})
    print('entregador selecionado:', picked)
    assert picked is not None

    assigned = atribuir_entrega(delivery_id, picked.get('id'))
    print('atribuída:', assigned)
    assert assigned and int(assigned.get('id')) == int(delivery_id)

    # 5) deletar mensagem da fila (ack)
    ok = q.delete_message(receipt)
    print('delete message ok?', ok)

    # 6) validar no storage que a entrega ficou atribuída
    e = obter_entrega(delivery_id)
    print('entrega final:', e)
    assert e.get('id_entregador') is not None or e.get('assigned_driver_id') is not None or e.get('assigned_driver_id') == picked.get('id') or e.get('id_entregador') == picked.get('id')

    print('Teste de integração concluído com sucesso')


if __name__ == '__main__':
    main()
