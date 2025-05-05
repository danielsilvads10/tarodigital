# -*- coding: utf-8 -*-
import uuid # Para gerar códigos únicos
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.sql import expression # Importar para server_default

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Modificado para incluir 'afiliado'
    role = db.Column(db.String(20), nullable=False, default='cliente') # 'cliente', 'admin', 'afiliado'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Novos campos para Afiliados e Convites (conforme design_afiliados_convites.md)
    affiliate_code = db.Column(db.String(20), unique=True, nullable=True) # Código único do afiliado
    referred_by_affiliate_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) # ID do afiliado que indicou
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) # ID do usuário que convidou

    # Novo campo para Acesso Premium - Usando server_default
    has_premium_access = db.Column(db.Boolean, nullable=False, server_default=expression.false())

    # Relacionamentos
    # Usuários que este afiliado indicou (um afiliado pode indicar muitos usuários)
    referrals = db.relationship('Usuario', 
                                foreign_keys=[referred_by_affiliate_id], 
                                backref=db.backref('referrer', remote_side=[id]), 
                                lazy='dynamic')
    
    # Usuários que este usuário convidou (um usuário pode convidar muitos usuários)
    invited_users = db.relationship('Usuario', 
                                    foreign_keys=[invited_by_user_id], 
                                    backref=db.backref('inviter', remote_side=[id]), 
                                    lazy='dynamic')

    # Conversões geradas por este afiliado (um afiliado pode ter muitas conversões)
    conversions_generated = db.relationship('AfiliadoConversao', 
                                            foreign_keys='AfiliadoConversao.affiliate_id', 
                                            backref='affiliate', 
                                            lazy='dynamic')

    # Conversão que gerou este usuário (um usuário pode ter sido gerado por uma conversão)
    conversion_entry = db.relationship('AfiliadoConversao', 
                                       foreign_keys='AfiliadoConversao.converted_user_id', 
                                       backref='converted_user', 
                                       uselist=False) # Um usuário é gerado por no máximo uma conversão de registro

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Função para gerar código de afiliado único (pode ser chamada quando role='afiliado')
    def generate_affiliate_code(self):
        if self.role == 'afiliado' and not self.affiliate_code:
            # Gera um código curto e único
            # Tenta algumas vezes para garantir unicidade (improvável colisão, mas seguro)
            for _ in range(5):
                code = str(uuid.uuid4().hex)[:8].upper() # Código de 8 caracteres
                if not Usuario.query.filter_by(affiliate_code=code).first():
                    self.affiliate_code = code
                    return code
            # Se falhar após 5 tentativas, usar um mais longo
            self.affiliate_code = str(uuid.uuid4().hex)[:12].upper()
            return self.affiliate_code
        return self.affiliate_code

    def __repr__(self):
        return f'<Usuario {self.username} (ID: {self.id}, Role: {self.role}, Premium: {self.has_premium_access})>'

class Acesso(db.Model):
    __tablename__ = 'acessos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) # Permitir nulo para acessos não autenticados
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)

    usuario = db.relationship('Usuario', backref=db.backref('acessos', lazy='dynamic'))

    def __repr__(self):
        return f'<Acesso {self.id} - {self.action} por {self.user_id or "Anonimo"}>'

class RespostaJornada(db.Model):
    __tablename__ = 'respostas_jornada'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    journey_id = db.Column(db.String(50), nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref=db.backref('respostas', lazy='dynamic'))

    def __repr__(self):
        return f'<Resposta {self.id} - Usuario {self.user_id} Jornada {self.journey_id} Q{self.question_id}>'

# Nova Tabela para Conversões de Afiliados (conforme design_afiliados_convites.md)
class AfiliadoConversao(db.Model):
    __tablename__ = 'afiliado_conversoes'
    id = db.Column(db.Integer, primary_key=True)
    affiliate_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False) # ID do afiliado
    converted_user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) # ID do usuário que se registrou/comprou
    conversion_type = db.Column(db.String(50), nullable=False) # Ex: 'registro', 'compra_produto_1990'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    value = db.Column(db.Float, nullable=True) # Adicionado para registrar valor da compra
    details = db.Column(db.Text, nullable=True) # Ex: ID da compra, etc.

    # Relacionamentos definidos na classe Usuario usando backref

    def __repr__(self):
        return f'<Conversao {self.id} - Afiliado {self.affiliate_id} Tipo {self.conversion_type} Valor {self.value}>'

