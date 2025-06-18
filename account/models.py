from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=12)

    def __str__(self) -> str:
        return f'{self.user.first_name} in {self.company.first()}'


class Company(models.Model):
    employees = models.ManyToManyField(Employee, related_name='company')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)
    instance.employee.save()
