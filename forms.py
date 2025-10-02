from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

class TransactionForm(FlaskForm):
    type = SelectField('Tipo', choices=[('expense','Despesa'), ('income','Receita')], validators=[DataRequired()])
    amount = DecimalField('Valor', places=2, rounding=None, validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    category = SelectField('Categoria', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Descrição')
    payment_method = StringField('Método de pagamento')
    submit = SubmitField('Salvar')

class CategoryForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    type = SelectField('Tipo', choices=[('expense','Despesa'), ('income','Receita')], validators=[DataRequired()])
    color = StringField('Cor (hex)')
    submit = SubmitField('Salvar')