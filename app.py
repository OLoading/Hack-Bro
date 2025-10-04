from flask import Flask, render_template, redirect, url_for, request, flash, Response, send_file
from config import Config
from models import db, Category, Transaction
from forms import TransactionForm, CategoryForm
from datetime import datetime, date
from decimal import Decimal
import os
import csv
import pandas as pd
from io import StringIO, BytesIO

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

    # -------------------------------
    
    @app.route('/')
    def index():
    # filtros opcionais
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

    # filtro por mês/ano
        month = request.args.get('month')
        year = request.args.get('year')

        if not month or not year:
            today = date.today()
            month_num = today.month
            year = today.year
        else:
                month_num = int(month)
        year = int(year)

        from_date = date(year, month_num, 1)
        if month_num == 12:
            to_date = date(year + 1, 1, 1)
        else:
            to_date = date(year, month_num + 1, 1)

        summary_q = Transaction.query.filter(
            Transaction.date >= from_date,
            Transaction.date < to_date
    )

        total_income = sum([t.amount for t in summary_q.join(Category).filter(Category.type == 'income').all()]) or Decimal('0.00')
        total_expense = sum([t.amount for t in summary_q.join(Category).filter(Category.type == 'expense').all()]) or Decimal('0.00')
        balance = total_income - total_expense

        categories = Category.query.all()

    # 🔹 IMPORTANTE: esse return precisa estar alinhado com o def
        return render_template(
            'index.html',
            transactions=transactions,
            categories=categories,
            total_income=total_income,
            total_expense=total_expense,
            balance=balance,
            month=f"{year}-{month_num:02d}",
            current_month=date.today().month,
            current_year=date.today().year
        )

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

    # -------------------------------
    # CRUD de Categorias
    # -------------------------------

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

    @app.route('/categories/<int:id>/edit', methods=['GET','POST'])
    def edit_category(id):
        c = Category.query.get_or_404(id)
        form = CategoryForm(obj=c)
        if form.validate_on_submit():
            c.name = form.name.data
            c.type = form.type.data
            c.color = form.color.data
            db.session.commit()
            flash('Categoria atualizada', 'success')
            return redirect(url_for('categories_view'))
        categories = Category.query.order_by(Category.type).all()
        return render_template('categories.html', categories=categories, form=form, edit_id=c.id)

    @app.route('/categories/<int:id>/delete', methods=['POST'])
    def delete_category(id):
        c = Category.query.get_or_404(id)
        db.session.delete(c)
        db.session.commit()
        flash('Categoria removida', 'info')
        return redirect(url_for('categories_view'))
    
        # -------------------------------
    # Exportação CSV e Excel (detalhado)
    # -------------------------------

    @app.route('/export/csv')
    def export_csv():
        transactions = Transaction.query.order_by(Transaction.date.desc()).all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor', 'Método'])
        for t in transactions:
            writer.writerow([
                t.date.strftime('%d/%m/%Y'),
                t.description,
                t.category.name if t.category else '',
                t.category.type if t.category else '',
                str(t.amount),
                t.payment_method
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=relatorio.csv"}
        )

    @app.route('/export/excel')
    def export_excel():
        transactions = Transaction.query.order_by(Transaction.date.desc()).all()

        data = []
        for t in transactions:
            data.append({
                'Data': t.date.strftime('%d/%m/%Y'),
                'Descrição': t.description,
                'Categoria': t.category.name if t.category else '',
                'Tipo': t.category.type if t.category else '',
                'Valor': float(t.amount),
                'Método': t.payment_method
            })

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Transações")

        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="relatorio.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -------------------------------
    # Exportação Resumida por Categoria
    # -------------------------------

    @app.route('/export/summary/csv')
    def export_summary_csv():
        summary = (
            db.session.query(Category.name, Category.type, db.func.sum(Transaction.amount))
            .join(Transaction, Transaction.category_id == Category.id)
            .group_by(Category.id)
            .all()
        )

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Categoria', 'Tipo', 'Total'])
        for name, typ, total in summary:
            writer.writerow([name, typ, float(total or 0)])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=resumo_categorias.csv"}
        )

    @app.route('/export/summary/excel')
    def export_summary_excel():
        summary = (
            db.session.query(Category.name, Category.type, db.func.sum(Transaction.amount))
            .join(Transaction, Transaction.category_id == Category.id)
                       .group_by(Category.id)
            .all()
        )

        data = []
        for name, typ, total in summary:
            data.append({
                'Categoria': name,
                'Tipo': typ,
                'Total': float(total or 0)
            })

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Resumo por Categoria")

        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="resumo_categorias.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    @app.route('/reset', methods=['POST'])
    def reset_data():
        # Apaga todas as transações e categorias
        Transaction.query.delete()
        Category.query.delete()
        db.session.commit()

        # Recria categorias padrão
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

        flash('Todos os dados foram apagados e categorias recriadas.', 'warning')
        return redirect(url_for('index'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)