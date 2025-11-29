import time
import os
import json
import logging

from queue import get_queue
from storage import listar_entregadores, atribuir_entrega

POLL_INTERVAL = float(os.getenv('WORKER_POLL_INTERVAL', '2'))
STATE_FILE = os.path.join(os.path.dirname(__file__), 'worker_state.json')

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger('delivery-worker')


def load_state():
    if not os.path.exists(STATE_FILE):
        return {'last_index': 0}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'last_index': 0}


def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning('falha ao salvar estado: %s', e)


def selecionar_entregador_round_robin(drivers, state):
    if not drivers:
        return None
    idx = state.get('last_index', 0) or 0
    pick = drivers[idx % len(drivers)]
    state['last_index'] = (idx + 1) % max(1, len(drivers))
    save_state(state)
    return pick


def executar():
    logger.info('Worker iniciado. Poll interval=%ss', POLL_INTERVAL)
    q = get_queue()
    state = load_state()

    try:
        while True:
            try:
                msg = q.receive_message()
            except Exception as e:
                logger.error('erro ao receber mensagem da fila: %s', e)
                time.sleep(POLL_INTERVAL)
                continue

            if not msg:
                time.sleep(POLL_INTERVAL)
                continue

            delivery = msg.get('entrega') or msg.get('delivery')
            receipt = msg.get('ReceiptHandle') or msg.get('receipt')
            if not delivery:
                logger.warning('mensagem sem payload válido: %s', msg)
                continue

            delivery_id = delivery.get('id')
            logger.info('Recebida mensagem para entrega id=%s', delivery_id)

            drivers = listar_entregadores()
            if not drivers:
                logger.warning('Nenhum entregador cadastrado. Re-enfileirando a entrega %s', delivery_id)
                try:
                    q.send_message(delivery_id)
                except Exception as e:
                    logger.error('falha ao reenfileirar: %s', e)
                time.sleep(POLL_INTERVAL)
                continue

            driver = selecionar_entregador_round_robin(drivers, state)
            if not driver:
                logger.error('falha ao selecionar entregador para entrega %s', delivery_id)
                time.sleep(POLL_INTERVAL)
                continue

            try:
                assigned = atribuir_entrega(delivery_id, driver.get('id'))
                if not assigned:
                    logger.error('falha ao atribuir entrega %s ao entregador %s', delivery_id, driver.get('id'))
                    # opcional: reenfileirar
                    try:
                        q.send_message(delivery_id)
                    except Exception as e:
                        logger.error('falha ao reenfileirar: %s', e)
                    # Mesmo se reenfileirar, deletar a mensagem atual (ack) para evitar loop
                    try:
                        if receipt:
                            q.delete_message(receipt)
                    except Exception:
                        logger.warning('falha ao deletar mensagem original')
                else:
                    logger.info('Entrega %s atribuída ao entregador %s (%s)', delivery_id, driver.get('id'), driver.get('name'))
                    # ack/delete da mensagem processada
                    try:
                        if receipt:
                            q.delete_message(receipt)
                    except Exception:
                        logger.warning('falha ao deletar mensagem após atribuição')
            except Exception as e:
                logger.exception('erro ao atribuir entrega: %s', e)
                try:
                    q.send_message(delivery_id)
                except Exception:
                    logger.error('falha ao reenfileirar depois de erro')
                # após reenfileirar, tentar deletar a mensagem original para não duplicar
                try:
                    if receipt:
                        q.delete_message(receipt)
                except Exception:
                    logger.warning('falha ao deletar mensagem original depois de erro')

            # pequeno delay antes de continuar
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info('Worker interrompido pelo usuário')


if __name__ == '__main__':
    executar()
