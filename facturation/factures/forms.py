from django import forms
from django.forms import modelformset_factory
from .models import LineItem, Invoice


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "customer",
            "customer_email",
            "billing_address",
            "date",
            "due_date",
            "message",
            "draft",
        ]
        widgets = {
            "customer": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Customer/Company Name"}
            ),
            "customer_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "customer@company.com"}
            ),
            "billing_address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": ""}
            ),
            "date": forms.DateInput(
                attrs={"class": "form-control", "placeholder": "YYYY-MM-DD"}
            ),
            "due_date": forms.DateInput(
                attrs={"class": "form-control", "placeholder": "YYYY-MM-DD"}
            ),
            "message": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Message"}
            ),
            "draft": forms.Select(
                choices=[(True, "Brouillon"), (False, "Comptabilisé")],
                attrs={"class": "form-control"},
            ),
        }


class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ["service", "description", "quantity", "rate"]
        widgets = {
            "service": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Service Name"}
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Description"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Quantity"}
            ),
            "rate": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Rate"}
            ),
        }


LineItemFormset = modelformset_factory(
    LineItem, form=LineItemForm, extra=1, can_delete=True
)
