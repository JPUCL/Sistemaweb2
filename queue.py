import os
import json
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from storage import USAR_TINYDB, obter_entrega, enviar_mensagem_fila, receber_mensagem_fila, deletar_mensagem_fila


class SQSQueue:
 
    def __init__(self):
        self.queue_url = os.getenv('AWS_SQS_QUEUE_URL')
        if not self.queue_url:
            raise RuntimeError('variável AWS_SQS_QUEUE_URL não definida')
        self.region = os.getenv('AWS_REGION')
        self.client = boto3.client('sqs', region_name=self.region) if self.region else boto3.client('sqs')

    def send_message(self, delivery_id: int):
        body = json.dumps({'id_entrega': int(delivery_id)})
        try:
            resp = self.client.send_message(QueueUrl=self.queue_url, MessageBody=body)
            return {'MessageId': resp.get('MessageId')}
        except (BotoCoreError, ClientError) as e:
            raise

    def receive_message(self):
        try:
            resp = self.client.receive_message(QueueUrl=self.queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1)
        except (BotoCoreError, ClientError) as e:
            raise
        messages = resp.get('Messages')
        if not messages:
            return None
        msg = messages[0]
        body = msg.get('Body')
        try:
            payload = json.loads(body)
            delivery_id = int(payload.get('id_entrega') or payload.get('delivery_id'))
        except Exception:
            # se a mensagem estiver malformada, deletá-la para evitar loop
            try:
                self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=msg.get('ReceiptHandle'))
            except Exception:
                pass
            return None

        # NÃO deletar imediatamente — retornar ReceiptHandle para permitir delete/ack explícito
        delivery = obter_entrega(delivery_id)
        return {'MessageId': msg.get('MessageId'), 'ReceiptHandle': msg.get('ReceiptHandle'), 'entrega': delivery}

    def delete_message(self, receipt_handle: str):
        try:
            resp = self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
            return True
        except Exception:
            return False


def get_queue():
    
   
    if USE_TINYDB:
        class TinyDBQueue:
            def send_message(self, delivery_id: int):
                return enviar_mensagem_fila(delivery_id)

            def receive_message(self):
                return receber_mensagem_fila()

            def delete_message(self, receipt_handle: str):
                return deletar_mensagem_fila(receipt_handle)

        return TinyDBQueue()

    return SQSQueue()
