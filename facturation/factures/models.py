from django.db import models
import datetime
from decimal import Decimal

class Invoice(models.Model):
    customer = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    date = models.DateField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    message = models.TextField(default="This is a default message.", blank=True)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    status = models.BooleanField(default=False)
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    draft = models.BooleanField(default=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, blank=True)

    def __str__(self):
        return str(self.customer)

    def get_status(self):
        return self.status

    def can_edit(self):
        return self.draft

    def save(self, *args, **kwargs):
        if not self.pk:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    def generate_invoice_number(self):
        chosen_date = self.date if self.date else datetime.datetime.now().date()
        current_year = chosen_date.year
        current_month = chosen_date.month

        # Get the last invoice globally
        last_invoice = Invoice.objects.order_by('-id').first()
        
        if last_invoice:
            # Extract the last number part and increment
            last_number = int(last_invoice.invoice_number.split('/')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"FAC/{current_year}/{current_month:02d}/{new_number:04d}"


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    service = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.service} for {self.invoice}"

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.quantity) * Decimal(self.rate) if self.quantity and self.rate else Decimal("0.00")
        super().save(*args, **kwargs)
