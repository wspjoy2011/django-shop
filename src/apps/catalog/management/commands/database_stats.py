from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.termcolors import make_style
from django.db.utils import DatabaseError

User = get_user_model()


class Command(BaseCommand):
    help = 'Display database statistics for all models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Filter by specific app (e.g., catalog, ratings, accounts)',
        )
        parser.add_argument(
            '--format',
            choices=['table', 'simple'],
            default='table',
            help='Output format',
        )

    def handle(self, *args, **options):
        app_filter = options.get('app')
        output_format = options.get('format')

        header_style = make_style(opts=('bold',), fg='cyan')
        model_style = make_style(fg='green')
        count_style = make_style(opts=('bold',), fg='yellow')
        total_style = make_style(opts=('bold',), fg='red')

        models_data = []
        total_count = 0

        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model._meta.model_name

            if app_filter and app_label != app_filter:
                continue

            if app_label in ['admin', 'auth', 'contenttypes', 'sessions']:
                continue

            try:
                count = model.objects.count()
                models_data.append({
                    'app': app_label,
                    'model': model_name.title(),
                    'model_class': model.__name__,
                    'count': count
                })
                total_count += count
            except DatabaseError as e:
                self.stdout.write(
                    self.style.WARNING(f'Database error counting {app_label}.{model_name}: {e}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Unexpected error counting {app_label}.{model_name}: {e}')
                )

        models_data.sort(key=lambda x: (x['app'], x['model']))

        if output_format == 'table':
            self._display_table(models_data, total_count, header_style, model_style, count_style, total_style)
        else:
            self._display_simple(models_data, total_count, model_style, count_style, total_style)

    def _display_table(self, models_data, total_count, header_style, model_style, count_style, total_style):

        self.stdout.write(header_style('\n' + '=' * 80))
        self.stdout.write(header_style('DATABASE STATISTICS'.center(80)))
        self.stdout.write(header_style('=' * 80))

        self.stdout.write(header_style(f"{'App':<15} {'Model':<20} {'Count':<15}"))
        self.stdout.write(header_style('-' * 80))

        current_app = None
        for data in models_data:
            if current_app != data['app']:
                if current_app is not None:
                    self.stdout.write('-' * 50)
                current_app = data['app']

            app_name = data['app'] if current_app == data['app'] else ''
            count_formatted = f"{data['count']:,}"

            self.stdout.write(
                f"{app_name:<15} "
                f"{model_style(data['model_class']):<20} "
                f"{count_style(count_formatted):<15}"
            )

        self.stdout.write(header_style('-' * 80))
        total_formatted = f"{total_count:,}"
        self.stdout.write(
            f"{'TOTAL':<15} "
            f"{'All Models':<20} "
            f"{total_style(total_formatted):<15}"
        )
        self.stdout.write(header_style('=' * 80 + '\n'))

    def _display_simple(self, models_data, total_count, model_style, count_style, total_style):

        self.stdout.write('\nDatabase Statistics:')
        self.stdout.write('-' * 40)

        current_app = None
        for data in models_data:
            if current_app != data['app']:
                if current_app is not None:
                    self.stdout.write('')
                current_app = data['app']
                self.stdout.write(f'\nApp: {data["app"].upper()}')

            count_formatted = f"{data['count']:,}"
            self.stdout.write(
                f'  * {model_style(data["model_class"])}: {count_style(count_formatted)}'
            )

        self.stdout.write('-' * 40)
        total_formatted = f"{total_count:,}"
        self.stdout.write(f' Total records: {total_style(total_formatted)}')
        self.stdout.write('')
