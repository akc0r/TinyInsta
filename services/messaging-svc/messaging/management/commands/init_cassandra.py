from django.core.management.base import BaseCommand

from messaging import cql


class Command(BaseCommand):
    help = "Create the Cassandra keyspace and tables (idempotent)."

    def handle(self, *args, **options):
        # Touching the session triggers schema creation (CREATE ... IF NOT EXISTS).
        cql.session()
        self.stdout.write(self.style.SUCCESS("Cassandra schema ready"))
