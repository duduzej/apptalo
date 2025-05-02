from datetime import datetime
from ..models import Pedido

def gerar_numero_pedido():
    """Gera um número único para o pedido"""
    ano = datetime.now().year
    mes = datetime.now().month
    
    # Buscar o último pedido do mês atual
    ultimo_pedido = (Pedido.query
                    .filter(Pedido.numero.like(f'PED{ano}{mes:02d}%'))
                    .order_by(Pedido.numero.desc())
                    .first())
    
    if ultimo_pedido:
        ultimo_numero = int(ultimo_pedido.numero[-3:])
        novo_numero = ultimo_numero + 1
    else:
        novo_numero = 1
    
    return f'PED{ano}{mes:02d}{novo_numero:03d}'

def formatar_moeda(valor):
    """Formata um valor para moeda brasileira"""
    return f'R$ {valor:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

def calcular_total_itens(itens):
    """Calcula o total de uma lista de itens"""
    return sum(item.quantidade * item.valor_unitario for item in itens)

def status_pedido_valido(status):
    """Verifica se o status do pedido é válido"""
    status_validos = [
        'Aguardando Pagamento',
        'Aguardando aprovação da arte',
        'Em Produção',
        'Entregue',
        'Cancelado'
    ]
    return status in status_validos

def get_cor_status(status):
    """Retorna a cor correspondente ao status do pedido"""
    cores = {
        'Aguardando Pagamento': '#ffc107',
        'Aguardando aprovação da arte': '#9933CC',
        'Em Produção': '#0d6efd',
        'Entregue': '#198754',
        'Cancelado': '#dc3545'
    }
    return cores.get(status, '#6c757d') 