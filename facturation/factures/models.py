from django.db import models
import datetime
from decimal import Decimal


class Invoice(models.Model):
    customer = models.CharField(max_length=255)
    customer_email = models.EmailField(null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    message = models.TextField(default="This is a default message.")
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    status = models.BooleanField(default=False)  # type: ignore
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    draft = models.BooleanField(default=False)  # type: ignore

    def __str__(self):
        return str(self.customer)

    def get_status(self):
        return self.status

    def can_edit(self):
        return self.draft

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        try:
            super().save(*args, **kwargs)
            __import__("pprint").pprint("data saved successfully")
        except Exception as e:
            raise e

    def generate_invoice_number(self):
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        count = (
            Invoice.objects.filter(  # type: ignore
                date__year=current_year, date__month=current_month
            ).count()
            + 1
        )
        return f"FAC/{current_year}/{current_month:02d}/{count:04d}"


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    service = models.CharField(max_length=255)
    description = models.TextField()
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.service} for {self.invoice} amount {self.amount}"

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.quantity) * Decimal(self.rate)  # type: ignore
        super().save(*args, **kwargs)

    def total_amount(self):
        return self.amount
