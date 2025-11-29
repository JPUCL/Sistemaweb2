from flask import Flask, request, jsonify
import os
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from queue import get_queue
from botocore.exceptions import BotoCoreError, ClientError
from storage import (
    iniciar_armazenamento,
    criar_entregador,
    obter_entregador_por_nome,
    criar_entrega,
    listar_entregas,
    atribuir_entrega,
    atualizar_status_entrega,
    obter_entrega,
    criar_tabelas,
)


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)

    iniciar_armazenamento(app)
    jwt = JWTManager(app)

    @app.before_first_request
    def init_db():
        criar_tabelas()

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.route('/drivers/register', methods=['POST'])
    def register_driver():
        data = request.get_json() or {}
        name = data.get('name') or data.get('nome')
        phone = data.get('phone')
        password = data.get('password') or data.get('senha')
        if not name or not password:
            return jsonify({'msg': 'nome e senha são obrigatórios'}), 400
        hashed = generate_password_hash(password)
        d = criar_entregador(name, phone, hashed)
        return jsonify({'id': d['id'], 'nome': d['name']}), 201

    @app.route('/drivers/login', methods=['POST'])
    def login_driver():
        data = request.get_json() or {}
        name = data.get('name') or data.get('nome')
        password = data.get('password') or data.get('senha')
        if not name or not password:
            return jsonify({'msg': 'nome e senha são obrigatórios'}), 400
        driver = obter_entregador_por_nome(name)
        if not driver or not driver.get('password_hash') or not check_password_hash(driver.get('password_hash'), password):
            return jsonify({'msg': 'credenciais inválidas'}), 401
        access_token = create_access_token(identity=driver.get('id'))
        return jsonify({'token_acesso': access_token}), 200

    @app.route('/orders', methods=['POST'])
    def create_order():
        data = request.get_json() or {}
        restaurant = data.get('restaurant') or data.get('restaurante')
        pickup_address = data.get('pickup_address') or data.get('endereco_retirada')
        customer_address = data.get('customer_address') or data.get('endereco_cliente')
        if not restaurant or not pickup_address or not customer_address:
            return jsonify({'msg': 'restaurant, pickup_address e customer_address são obrigatórios'}), 400
        order = criar_entrega(restaurant, pickup_address, customer_address, status='enfileirado')
        
        try:
            q = get_queue()
            q.send_message(order['id'])
        except Exception as e:
            return jsonify({'msg': 'falha ao enfileirar mensagem no SQS', 'erro': str(e)}), 500
        return jsonify({'id': order['id'], 'status': order['status']}), 201

    @app.route('/orders', methods=['GET'])
    def list_orders():
        orders = listar_entregas()
        out = orders
        # resposta com campos em português já fornecida pela camada de storage
        return jsonify(out), 200

    @app.route('/driver/<int:driver_id>/next', methods=['GET'])
    @jwt_required()
    def driver_next(driver_id):
        # ensure token owner matches driver_id
        current = get_jwt_identity()
        if int(current) != int(driver_id):
            return jsonify({'msg': 'acesso proibido'}), 403
        # receive message from SQS
        try:
            q = get_queue()
            msg = q.receive_message()
        except Exception as e:
            return jsonify({'msg': 'falha ao receber do SQS', 'erro': str(e)}), 500
        if not msg:
            return jsonify({'msg': 'sem mensagens'}), 204
        delivery = msg.get('delivery')
        if not delivery:
            return jsonify({'msg': 'mensagem inválida'}), 500
        # atribuir ao entregador via storage
        assigned = atribuir_entrega(delivery.get('id'), driver_id)
        if not assigned:
            return jsonify({'msg': 'falha ao atribuir entrega'}), 500
        return jsonify({'id_entrega': assigned.get('id'), 'restaurante': assigned.get('restaurante'), 'endereco_retirada': assigned.get('endereco_retirada'), 'endereco_cliente': assigned.get('endereco_cliente'), 'status': assigned.get('status')}), 200

    @app.route('/driver/<int:driver_id>/pickup', methods=['POST'])
    @jwt_required()
    def driver_pickup(driver_id):
        current = get_jwt_identity()
        if int(current) != int(driver_id):
            return jsonify({'msg': 'acesso proibido'}), 403
        data = request.get_json() or {}
        delivery_id = data.get('delivery_id') or data.get('id_entrega')
        delivery = obter_entrega(delivery_id)
        if not delivery or int(delivery.get('assigned_driver_id') or 0) != int(driver_id):
            return jsonify({'msg': 'entrega não encontrada ou não atribuída ao entregador'}), 404
        updated = atualizar_status_entrega(delivery_id, 'coletado')
        if not updated:
            return jsonify({'msg': 'falha ao atualizar status'}), 500
        return jsonify({'id': updated.get('id'), 'status': updated.get('status')}), 200

    @app.route('/driver/<int:driver_id>/deliver', methods=['POST'])
    @jwt_required()
    def driver_deliver(driver_id):
        current = get_jwt_identity()
        if int(current) != int(driver_id):
            return jsonify({'msg': 'acesso proibido'}), 403
        data = request.get_json() or {}
        delivery_id = data.get('delivery_id') or data.get('id_entrega')
        delivery = obter_entrega(delivery_id)
        if not delivery or int(delivery.get('assigned_driver_id') or 0) != int(driver_id):
            return jsonify({'msg': 'entrega não encontrada ou não atribuída ao entregador'}), 404
        updated = atualizar_status_entrega(delivery_id, 'entregue')
        if not updated:
            return jsonify({'msg': 'falha ao atualizar status'}), 500
        return jsonify({'id': updated.get('id'), 'status': updated.get('status')}), 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
