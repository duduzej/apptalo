from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from ..models import Pedido, Usuario, Cliente
from ..extensions import db

admin = Blueprint('admin', __name__)

@admin.route('/pedidos')
@login_required
def pedidos():
    """Lista todos os pedidos para o administrador"""
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('main.index'))
    
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin/pedidos.html', pedidos=pedidos)

@admin.route('/pedidos/<int:id>/visualizar')
@login_required
def visualizar_pedido(id):
    """Visualiza um pedido específico"""
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado!', 'danger')
        return redirect(url_for('main.index'))
    
    pedido = Pedido.query.get_or_404(id)
    return render_template('admin/visualizar_pedido.html', pedido=pedido)

@admin.route('/pedidos/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_pedido(id):
    """Exclui um pedido"""
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    pedido = Pedido.query.get_or_404(id)
    db.session.delete(pedido)
    db.session.commit()
    
    return jsonify({'message': 'Pedido excluído com sucesso'}), 200

@admin.route('/pedidos/excluir-multiplos', methods=['POST'])
@login_required
def excluir_multiplos_pedidos():
    """Exclui múltiplos pedidos"""
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    data = request.get_json()
    pedidos_ids = data.get('pedidos', [])
    
    try:
        Pedido.query.filter(Pedido.id.in_(pedidos_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'message': 'Pedidos excluídos com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir pedidos'}), 500

@admin.route('/pedidos/excluir-todos', methods=['POST'])
@login_required
def excluir_todos_pedidos():
    """Exclui todos os pedidos"""
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        Pedido.query.delete()
        db.session.commit()
        return jsonify({'message': 'Todos os pedidos foram excluídos com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir pedidos'}), 500 