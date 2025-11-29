Implementação de referência (Flask)

Requisitos locais:
- Python 3.10+

Passos (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# variáveis de ambiente (exemplo)
$env:DATABASE_URL = 'sqlite:///app.db'
# habilitar TinyDB para desenvolvimento leve (opcional)
$env:USE_TINYDB = 'true'
# iniciar a API
python .\app.py
```

Endpoints principais (Fluxo de entregas):
- POST `/drivers/register` {name,phone,password} -> registra entregador
- POST `/drivers/login` {name,password} -> obtém `access_token` (JWT)
- POST `/orders` {restaurant,pickup_address,customer_address} -> cria pedido e enfileira
- GET `/orders` -> listar pedidos
- GET `/driver/{id}/next` -> entregador pega próxima entrega (consome fila)
- POST `/driver/{id}/pickup` {delivery_id} -> marca como `coletado`
- POST `/driver/{id}/deliver` {delivery_id} -> marca como `entregue`

Proteção dos endpoints do entregador:
- Os endpoints `GET /driver/{id}/next`, `POST /driver/{id}/pickup` e `POST /driver/{id}/deliver` exigem o token JWT obtido em `/drivers/login`.
- Informe o header `Authorization: Bearer <access_token>` nas requisições.

Usando AWS SQS (opcional)
-------------------------
Para usar uma fila SQS real, crie a fila na AWS e exporte as variáveis de ambiente (PowerShell exemplo):

```powershell
$env:AWS_ACCESS_KEY_ID = 'AKIA...'
$env:AWS_SECRET_ACCESS_KEY = '...'
$env:AWS_REGION = 'us-east-1'
$env:AWS_SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/minha-fila'
```

O arquivo `queue.py` usa `boto3` para enviar/receber mensagens. A mensagem esperada é JSON com o campo `delivery_id`, por exemplo: `{"delivery_id": 123}`.

Observações:
- Se o SQS não estiver configurado corretamente, chamadas de enfileiramento/recebimento retornarão erro com a descrição.
- Para desenvolvimento leve, use `USE_TINYDB=true` (persistência em `tinydb.json`).

Executando o worker (atribui entregas automaticamente)
----------------------------------------------------
Para rodar o worker que consome a fila e atribui entregas a entregadores cadastrados:

```powershell
$env:USE_TINYDB = 'true'  # ou 'false' para usar SQS
python .\worker.py
```

Notas finais:
- O projeto é uma POC simplificada; ajustes são necessários para produção (migrar para Postgres/DynamoDB, configurar observabilidade e autenticação/segurança reforçada).
