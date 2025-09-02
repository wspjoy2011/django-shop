from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Min, Max
from django.utils.termcolors import make_style

from apps.inventories.models import ProductInventory


class Command(BaseCommand):
    help = 'Display inventory statistics'

    def handle(self, *args, **options):
        header_style = make_style(opts=('bold',), fg='cyan')
        section_style = make_style(opts=('bold',), fg='green')
        value_style = make_style(opts=('bold',), fg='yellow')
        percentage_style = make_style(fg='magenta')
        currency_style = make_style(fg='blue')

        total_inventory = ProductInventory.objects.count()

        if total_inventory == 0:
            self.stdout.write(
                self.style.WARNING('No inventory records found.')
            )
            return

        active_products = ProductInventory.objects.filter(is_active=True).count()
        in_stock_products = ProductInventory.objects.filter(stock_quantity__gt=0).count()
        out_of_stock_products = ProductInventory.objects.filter(stock_quantity=0).count()
        on_sale_products = ProductInventory.objects.filter(sale_price__isnull=False).count()

        price_stats = ProductInventory.objects.aggregate(
            avg_base_price=Avg('base_price'),
            min_base_price=Min('base_price'),
            max_base_price=Max('base_price'),
        )

        stock_stats = ProductInventory.objects.aggregate(
            avg_stock=Avg('stock_quantity'),
            min_stock=Min('stock_quantity'),
            max_stock=Max('stock_quantity'),
            avg_reserved=Avg('reserved_quantity'),
        )

        currency_dist = ProductInventory.objects.values('currency__code').annotate(
            count=Count('currency__code')
        ).order_by('-count')

        stock_ranges = [
            (0, 0, 'Out of stock'),
            (1, 10, 'Very low (1-10)'),
            (11, 50, 'Low (11-50)'),
            (51, 200, 'Medium (51-200)'),
            (201, 500, 'High (201-500)'),
            (501, 10000, 'Very high (501+)'),
        ]

        self.stdout.write(header_style('INVENTORY STATISTICS'))
        self.stdout.write(header_style('=' * 50))

        self.stdout.write(f'Total inventory records: {value_style(f"{total_inventory:,}")}')
        self.stdout.write(f'Active products: {value_style(f"{active_products:,}")} {percentage_style(f"({active_products / total_inventory * 100:.1f}%)")}')
        self.stdout.write(f'In stock: {value_style(f"{in_stock_products:,}")} {percentage_style(f"({in_stock_products / total_inventory * 100:.1f}%)")}')
        self.stdout.write(f'Out of stock: {value_style(f"{out_of_stock_products:,}")} {percentage_style(f"({out_of_stock_products / total_inventory * 100:.1f}%)")}')
        self.stdout.write(f'On sale: {value_style(f"{on_sale_products:,}")} {percentage_style(f"({on_sale_products / total_inventory * 100:.1f}%)")}')

        self.stdout.write(f'\n{section_style("PRICE STATISTICS")}')
        self.stdout.write(section_style('-' * 30))
        self.stdout.write(f'Average base price: {value_style(f"${price_stats["avg_base_price"]:.2f}")}')
        self.stdout.write(f'Min base price: {value_style(f"${price_stats["min_base_price"]:.2f}")}')
        self.stdout.write(f'Max base price: {value_style(f"${price_stats["max_base_price"]:.2f}")}')

        self.stdout.write(f'\n{section_style("STOCK STATISTICS")}')
        self.stdout.write(section_style('-' * 30))
        self.stdout.write(f'Average stock: {value_style(f"{stock_stats["avg_stock"]:.1f}")}')
        self.stdout.write(f'Min stock: {value_style(f"{stock_stats["min_stock"]}")}')
        self.stdout.write(f'Max stock: {value_style(f"{stock_stats["max_stock"]}")}')
        self.stdout.write(f'Average reserved: {value_style(f"{stock_stats["avg_reserved"]:.1f}")}')

        self.stdout.write(f'\n{section_style("CURRENCY DISTRIBUTION")}')
        self.stdout.write(section_style('-' * 30))
        for curr in currency_dist:
            percentage = curr['count'] / total_inventory * 100
            self.stdout.write(f'{currency_style(curr["currency__code"])}: {value_style(f"{curr["count"]:,}")} {percentage_style(f"({percentage:.1f}%)")}')

        self.stdout.write(f'\n{section_style("STOCK LEVEL DISTRIBUTION")}')
        self.stdout.write(section_style('-' * 30))
        for min_stock, max_stock, label in stock_ranges:
            if min_stock == max_stock:
                count = ProductInventory.objects.filter(stock_quantity=min_stock).count()
            else:
                count = ProductInventory.objects.filter(
                    stock_quantity__gte=min_stock,
                    stock_quantity__lte=max_stock
                ).count()

            percentage = count / total_inventory * 100
            self.stdout.write(f'{label}: {value_style(f"{count:,}")} {percentage_style(f"({percentage:.1f}%)")}')
