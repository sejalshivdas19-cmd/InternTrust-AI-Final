import getpass
import click

from app.extensions import db
from app.models import Admin, RiskSignal
from app.services.risk_signals_data import DEFAULT_RISK_SIGNALS


def register_cli(app):

    @app.cli.command("init-db")
    def init_db():
        """Create all database tables and seed default risk signals.
        Safe to run multiple times - it will not duplicate existing signals."""
        db.create_all()

        existing_codes = {s.signal_code for s in RiskSignal.query.all()}
        created = 0
        for signal in DEFAULT_RISK_SIGNALS:
            if signal["signal_code"] in existing_codes:
                continue
            db.session.add(RiskSignal(**signal))
            created += 1
        db.session.commit()
        click.echo(f"Database initialized. {created} risk signal(s) seeded.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    def create_admin(name, email):
        """Interactively and safely create the first administrator account.
        The password is never taken as a command-line argument (which would
        leak into shell history) - it is prompted for securely instead."""
        if Admin.query.filter_by(email=email.lower().strip()).first():
            click.echo("An administrator with that email already exists.")
            return

        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            click.echo("Passwords do not match. Aborted.")
            return
        if len(password) < 10:
            click.echo("Password must be at least 10 characters. Aborted.")
            return

        admin = Admin(name=name.strip(), email=email.lower().strip())
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrator '{email}' created successfully.")
