from django.contrib.auth import get_user_model
from faker import Faker
import factory

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    class Params:
        raw_password = "password123"

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}_{obj.last_name.lower()}@example.com")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if not create:
            return

        raw_password = extracted or kwargs.get('raw_password', 'password123')
        obj.set_password(raw_password)
        obj.save()
