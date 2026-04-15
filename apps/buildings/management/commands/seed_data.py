"""
Management command to populate the database with demo data.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random

from apps.accounts.models import User, Organization
from apps.buildings.models import Building, Tower, Apartment
from apps.measurements.models import Measurement


class Command(BaseCommand):
    help = 'Seed database with demo buildings, users, and measurements'

    def handle(self, *args, **options):
        self.stdout.write('Seeding data...')

        # ── Organization ──
        org, _ = Organization.objects.get_or_create(
            slug='hydroscan',
            defaults={'name': 'HydroScan'},
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Organization: {org.name}'))

        # ── Users ──
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Admin',
                'last_name': 'HydroScan',
                'email': 'admin@hydroscan.cl',
                'phone': '+56 9 1234 5678',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'organization': org,
            },
        )
        admin.set_password('admin')
        admin.organization = org
        admin.save()

        jperez, _ = User.objects.get_or_create(
            username='jperez',
            defaults={
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'email': 'jperez@hydroscan.cl',
                'phone': '+56 9 8765 4321',
                'role': 'operator',
                'organization': org,
            },
        )
        jperez.set_password('1234')
        jperez.organization = org
        jperez.save()

        mlopez, _ = User.objects.get_or_create(
            username='mlopez',
            defaults={
                'first_name': 'María',
                'last_name': 'López',
                'email': 'mlopez@hydroscan.cl',
                'phone': '+56 9 5555 1234',
                'role': 'operator',
                'organization': org,
            },
        )
        mlopez.set_password('1234')
        mlopez.organization = org
        mlopez.save()

        self.stdout.write(self.style.SUCCESS(f'  ✓ Users: admin, jperez, mlopez'))

        # ── Buildings ──
        bld1, _ = Building.objects.get_or_create(
            name='Edificio Los Robles',
            defaults={'address': 'Av. Providencia 1234, Santiago', 'organization': org},
        )
        bld1.organization = org
        bld1.save()
        bld2, _ = Building.objects.get_or_create(
            name='Condominio Parque Central',
            defaults={'address': 'Calle Las Flores 567, Ñuñoa', 'organization': org},
        )
        bld2.organization = org
        bld2.save()

        # ── Towers ──
        tA, _ = Tower.objects.get_or_create(building=bld1, name='Torre A')
        tB, _ = Tower.objects.get_or_create(building=bld1, name='Torre B')
        tC, _ = Tower.objects.get_or_create(building=bld1, name='Torre C')
        tN, _ = Tower.objects.get_or_create(building=bld2, name='Torre Norte')
        tS, _ = Tower.objects.get_or_create(building=bld2, name='Torre Sur')

        # ── Apartments ──
        apt_data = [
            # Los Robles — Torre A
            (tA, '101', 1, '621659-11'),
            (tA, '102', 1, '621660-12'),
            (tA, '201', 2, '621661-13'),
            (tA, '202', 2, '621662-14'),
            (tA, '203', 2, '785412-03'),
            (tA, '301', 3, '621663-15'),
            (tA, '405', 4, '369258-22'),
            # Los Robles — Torre B
            (tB, '201', 2, '147852-19'),
            (tB, '504', 5, '24081375'),
            (tB, '601', 6, '258147-06'),
            # Los Robles — Torre C
            (tC, '102', 1, '951753-14'),
            (tC, '302', 3, '963258-07'),
            # Parque Central — Torre Norte
            (tN, '101', 1, '550101-01'),
            (tN, '201', 2, '550201-02'),
            (tN, '301', 3, '550301-03'),
            # Parque Central — Torre Sur
            (tS, '101', 1, '560101-01'),
            (tS, '201', 2, '560201-02'),
        ]

        apartments = []
        for tower, number, floor, meter_id in apt_data:
            apt, _ = Apartment.objects.get_or_create(
                tower=tower, number=number,
                defaults={'floor': floor, 'meter_id': meter_id},
            )
            apartments.append(apt)

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Buildings: {Building.objects.count()}, '
            f'Towers: {Tower.objects.count()}, '
            f'Apartments: {Apartment.objects.count()}'
        ))

        # ── Assign apartments to operators ──
        torre_a_apts = Apartment.objects.filter(tower=tA)
        torre_b_apts = Apartment.objects.filter(tower=tB)
        torre_c_apts = Apartment.objects.filter(tower=tC)

        jperez.assigned_apartments.set(list(torre_a_apts) + list(torre_b_apts))
        mlopez.assigned_apartments.set(list(torre_c_apts) + list(Apartment.objects.filter(tower__building=bld2)))

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Assignments: jperez={jperez.assigned_apartments.count()}, '
            f'mlopez={mlopez.assigned_apartments.count()}'
        ))

        # ── Measurements (demo) ──
        if Measurement.objects.count() == 0:
            statuses = ['verified', 'pending_review', 'rejected']
            operators = [jperez, mlopez]
            now = timezone.now()

            for apt in apartments:
                for i in range(random.randint(2, 5)):
                    Measurement.objects.create(
                        apartment=apt,
                        operator=random.choice(operators),
                        reading_value=Decimal(str(round(random.uniform(10, 999), 1))),
                        unit='m³',
                        status=random.choices(statuses, weights=[6, 3, 1])[0],
                        meter_type=random.choice(['analog', 'digital_drum', 'digital']),
                        latitude=Decimal(str(round(-33.4 + random.uniform(-0.05, 0.05), 7))),
                        longitude=Decimal(str(round(-70.6 + random.uniform(-0.05, 0.05), 7))),
                        captured_at=now - timezone.timedelta(days=random.randint(0, 60), hours=random.randint(0, 23)),
                    )

            self.stdout.write(self.style.SUCCESS(f'  ✓ Measurements: {Measurement.objects.count()}'))
        else:
            self.stdout.write(self.style.WARNING('  ⊘ Measurements already exist, skipped'))

        self.stdout.write(self.style.SUCCESS('\n✅ Seed complete!'))
