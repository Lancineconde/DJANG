from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.http import HttpResponse
from django.views import View
from django.db.models import Q
from django.core.paginator import Paginator
from .models import LineItem, Invoice
from .forms import LineItemFormset, InvoiceForm
import pdfkit

class InvoiceListView(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        status_filter = request.GET.get('status', '')
        date_filter = request.GET.get('date', '')
        completion_filter = request.GET.get('completion', '')
        draft_filter = request.GET.get('draft', '')

        invoices = Invoice.objects.all()

        if query:
            invoices = invoices.filter(Q(customer__icontains=query) | Q(invoice_number__icontains=query))

        if status_filter:
            invoices = invoices.filter(status=(status_filter == '1'))

        if date_filter:
            now = datetime.now().date()
            if date_filter == 'past':
                invoices = invoices.filter(due_date__lt=now)
            elif date_filter == 'future':
                invoices = invoices.filter(due_date__gte=now)

        if completion_filter:
            if completion_filter == 'completed':
                invoices = invoices.filter(draft=False)
            elif completion_filter == 'draft':
                invoices = invoices.filter(draft=True)

        paginator = Paginator(invoices, 10)  # Show 10 invoices per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        for invoice in page_obj:
            if invoice.due_date and invoice.due_date > datetime.now().date():
                invoice.days_remaining = (invoice.due_date - datetime.now().date()).days
            else:
                invoice.days_remaining = 0

            tax_rate = invoice.tax_percentage / 100
            invoice.subtotal = invoice.total_amount / (1 + tax_rate) if invoice.total_amount else Decimal("0.00")
            invoice.tax = invoice.total_amount - invoice.subtotal if invoice.total_amount else Decimal("0.00")
            print(f"Invoice {invoice.id}: Subtotal {invoice.subtotal}, Tax {invoice.tax}")

        context = {
            "invoices": page_obj,
            "query": query,
            "status_filter": status_filter,
            "date_filter": date_filter,
            "completion_filter": completion_filter,
            "draft_filter": draft_filter,
        }
        return render(request, "factures/invoice_list.html", context)

    def post(self, request):
        invoice_ids = request.POST.getlist("invoice_id")
        invoice_ids = list(map(int, invoice_ids))

        if "status" in request.POST:
            update_status_for_invoices = int(request.POST["status"])
            invoices = Invoice.objects.filter(id__in=invoice_ids)

            if update_status_for_invoices == 0:
                invoices.update(status=False)
            else:
                invoices.update(status=True)

        if "draft" in request.POST:
            invoice_id = request.POST.get("invoice_id")
            invoice = get_object_or_404(Invoice, id=invoice_id)
            draft_status = bool(int(request.POST["draft"]))
            invoice.draft = draft_status
            invoice.save()

        return redirect("factures:invoice-list")

def create_or_edit_invoice(request, id=None):
    if id:
        invoice = get_object_or_404(Invoice, id=id)
        heading_message = "Edit Invoice"
    else:
        invoice = Invoice(
            date=datetime.now().date(),
            due_date=datetime.now().date() + timedelta(days=30),
            draft=True,
        )
        invoice.save()  # Ensure the invoice is saved before passing to the formset
        heading_message = "Create Invoice"

    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = LineItemFormset(request.POST, queryset=LineItem.objects.filter(invoice=invoice))

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.save()

            total = Decimal("0.00")
            invoice.lineitem_set.all().delete()  # Delete existing line items
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get("DELETE"):
                    service = form.cleaned_data.get("service")
                    description = form.cleaned_data.get("description")
                    quantity = form.cleaned_data.get("quantity")
                    rate = form.cleaned_data.get("rate")
                    if service and description and quantity and rate:
                        amount = Decimal(rate) * Decimal(quantity)
                        total += amount
                        line_item = LineItem(
                            invoice=invoice,
                            service=service,
                            description=description,
                            quantity=quantity,
                            rate=rate,
                            amount=amount,
                        )
                        line_item.save()

            tax = total * (invoice.tax_percentage / 100)
            total_with_tax = total + tax
            invoice.total_amount = total_with_tax
            invoice.save()
            print(f"Saved Invoice {invoice.id}: Subtotal {total}, Tax {tax}, Total {total_with_tax}")

            return redirect(reverse("factures:invoice-list"))
        else:
            print("Form or formset is invalid")
            print(f"Form errors: {form.errors}")
            for i, form in enumerate(formset):
                print(f"Formset form {i} errors: {form.errors}")

    else:
        form = InvoiceForm(instance=invoice)
        formset = LineItemFormset(queryset=LineItem.objects.filter(invoice=invoice))

    context = {
        "title": heading_message,
        "form": form,
        "formset": formset,
        "invoice_id": invoice.invoice_number if invoice else None,
        "invoice": invoice,
    }
    return render(
        request,
        "factures/invoice_edit.html" if id else "factures/invoice_create.html",
        context,
    )

def view_PDF(request, id=None):
    invoice = get_object_or_404(Invoice, id=id)
    lineitem = invoice.lineitem_set.all()

    tax_rate = invoice.tax_percentage / 100 if invoice.tax_percentage else Decimal("0.00")

    if invoice.total_amount is None:
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
    else:
        subtotal = invoice.total_amount / (1 + tax_rate)
        tax = invoice.total_amount - subtotal

    context = {
        "company": {
            "name": "R & S TELECOM ",
            "address": "8 rue des frères caudron 78140 vélizy-villacoublay",
            "phone": "(818) XXX XXXX",
            "email": "contact@rs-telecom.fr",
        },
        "invoice_id": invoice.invoice_number,
        "invoice_total": invoice.total_amount,
        "customer": invoice.customer,
        "customer_email": invoice.customer_email,
        "date": invoice.date,
        "due_date": invoice.due_date,
        "billing_address": invoice.billing_address,
        "message": invoice.message,
        "lineitem": lineitem,
        "tax": tax,
        "subtotal": subtotal,
    }
    return render(request, "factures/pdf_template.html", context)

def generate_PDF(request, id):
    pdf = pdfkit.from_url(
        request.build_absolute_uri(reverse("factures:view-pdf", args=[id])), False
    )
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="invoice.pdf"'
    return response
