from flask import Flask, render_template, redirect, url_for, request, flash
from config import Config
from models import db, Category, Transaction
from forms import TransactionForm, CategoryForm
from datetime import date
from decimal import Decimal
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        os.makedirs(os.path.join(app.root_path, 'data'), exist_ok=True)
        db.create_all()
        # seed categories if empty
        if Category.query.count() == 0:
            defaults = [
                ('Salário','income','#16a34a'),
                ('Presente','income','#059669'),
                ('Alimentação','expense','#ef4444'),
                ('Transporte','expense','#f97316'),
                ('Lazer','expense','#8b5cf6'),
            ]
            for name, typ, color in defaults:
                db.session.add(Category(name=name, type=typ, color=color))
            db.session.commit()

    @app.route('/')
    def index():
        start = request.args.get('start')
        end = request.args.get('end')
        cat = request.args.get('category', type=int)

        q = Transaction.query.order_by(Transaction.date.desc())
        if start:
            q = q.filter(Transaction.date >= start)
        if end:
            q = q.filter(Transaction.date <= end)
        if cat:
            q = q.filter(Transaction.category_id == cat)

        transactions = q.all()
        # resumo do mês atual por padrão
        month = request.args.get('month')
        if not month:
            month = date.today().strftime('%Y-%m')
        year, month_num = map(int, month.split('-'))
        from_date = date(year, month_num, 1)
        if month_num == 12:
            to_date = date(year+1, 1, 1)
        else:
            to_date = date(year, month_num+1, 1)

        summary_q = Transaction.query.filter(Transaction.date >= from_date).filter(Transaction.date < to_date)
        total_income = sum([t.amount for t in summary_q.join(Category).filter(Category.type=='income').all()]) or Decimal('0.00')
        total_expense = sum([t.amount for t in summary_q.join(Category).filter(Category.type=='expense').all()]) or Decimal('0.00')
        balance = total_income - total_expense

        categories = Category.query.all()
        return render_template('index.html', transactions=transactions, categories=categories,
                               total_income=total_income, total_expense=total_expense, balance=balance, month=month)

    @app.route('/transaction/new', methods=['GET','POST'])
    def new_transaction():
        form = TransactionForm()
        form.category.choices = [(c.id, f"{c.name} [{c.type}]") for c in Category.query.all()]

        if form.validate_on_submit():
            t = Transaction(
                category_id=form.category.data,
                amount=Decimal(str(form.amount.data)),
                date=form.date.data,
                description=form.description.data,
                payment_method=form.payment_method.data
            )
            db.session.add(t)
            db.session.commit()
            flash('Transação salva', 'success')
            return redirect(url_for('index'))
        return render_template('transaction_form.html', form=form)

    @app.route('/transaction/<int:id>/edit', methods=['GET','POST'])
    def edit_transaction(id):
        t = Transaction.query.get_or_404(id)
        form = TransactionForm()
        form.category.choices = [(c.id, f"{c.name} [{c.type}]") for c in Category.query.all()]

        if request.method == 'GET':
            form.amount.data = float(t.amount)
            form.date.data = t.date
            form.type.data = t.category.type if t.category else 'expense'
            form.category.data = t.category_id
            form.description.data = t.description
            form.payment_method.data = t.payment_method

        if form.validate_on_submit():
            t.amount = Decimal(str(form.amount.data))
            t.date = form.date.data
            t.category_id = form.category.data
            t.description = form.description.data
            t.payment_method = form.payment_method.data
            db.session.commit()
            flash('Transação atualizada', 'success')
            return redirect(url_for('index'))
        return render_template('transaction_form.html', form=form, edit=True)

    @app.route('/transaction/<int:id>/delete', methods=['POST'])
    def delete_transaction(id):
        t = Transaction.query.get_or_404(id)
        db.session.delete(t)
        db.session.commit()
        flash('Transação removida', 'info')
        return redirect(url_for('index'))

    @app.route('/categories', methods=['GET','POST'])
    def categories_view():
        form = CategoryForm()
        if form.validate_on_submit():
            c = Category(name=form.name.data, type=form.type.data, color=form.color.data)
            db.session.add(c)
            db.session.commit()
            flash('Categoria criada', 'success')
            return redirect(url_for('categories_view'))
        categories = Category.query.order_by(Category.type).all()
        return render_template('categories.html', categories=categories, form=form)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)