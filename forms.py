from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired

class TransactionForm(FlaskForm):
    amount = DecimalField('Valor', validators=[DataRequired()])
    date = DateField('Data', validators=[DataRequired()])
    category = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    description = StringField('Descrição')
    payment_method = SelectField('Método de Pagamento', choices=[
        ('dinheiro', 'Dinheiro'),
        ('cartao', 'Cartão'),
        ('pix', 'Pix'),
        ('boleto', 'Boleto')
    ])
    submit = SubmitField('Salvar')

class CategoryForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    type = SelectField('Tipo', choices=[
        ('income', 'Receita'),
        ('expense', 'Despesa')
    ], validators=[DataRequired()])
    color = StringField('Cor (hex)', validators=[DataRequired()])
    submit = SubmitField('Salvar')