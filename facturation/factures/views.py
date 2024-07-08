from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.http import HttpResponse
from django.views import View
from .models import LineItem, Invoice
from .forms import LineItemFormset, InvoiceForm
import pdfkit

class InvoiceListView(View):
    def get(self, request, *args, **kwargs):
        invoices = Invoice.objects.all()
        for invoice in invoices:
            invoice.days_remaining = (invoice.due_date - datetime.now().date()).days
            if invoice.total_amount:
                invoice.subtotal = invoice.total_amount / Decimal('1.20')
                invoice.tax = invoice.total_amount - invoice.subtotal
            else:
                invoice.subtotal = Decimal('0.00')
                invoice.tax = Decimal('0.00')
        context = {
            "invoices": invoices,
        }
        return render(request, 'factures/invoice_list.html', context)

    def post(self, request):
        invoice_ids = request.POST.getlist("invoice_id")
        invoice_ids = list(map(int, invoice_ids))

        if 'status' in request.POST:
            update_status_for_invoices = int(request.POST['status'])
            invoices = Invoice.objects.filter(id__in=invoice_ids)

            if update_status_for_invoices == 0:
                invoices.update(status=False)
            else:
                invoices.update(status=True)
        
        if 'draft' in request.POST:
            invoice_id = request.POST.get('invoice_id')
            invoice = get_object_or_404(Invoice, id=invoice_id)
            draft_status = bool(int(request.POST['draft']))
            invoice.draft = draft_status
            invoice.save()

        return redirect('factures:invoice-list')

def create_or_edit_invoice(request, id=None):
    if id:
        invoice = get_object_or_404(Invoice, id=id)
        heading_message = 'Edit Invoice'
    else:
        invoice = Invoice(date=datetime.now().date(), due_date=datetime.now().date() + timedelta(days=30), draft=True)
        invoice.save()
        heading_message = 'Create Invoice'

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = LineItemFormset(request.POST, queryset=LineItem.objects.filter(invoice=invoice))

        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            if 'create' in request.POST:
                invoice.draft = False  # Mark as finalized
            invoice.save()

            total = Decimal('0.00')
            invoice.lineitem_set.all().delete()
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    service = form.cleaned_data.get('service')
                    description = form.cleaned_data.get('description')
                    quantity = form.cleaned_data.get('quantity')
                    rate = form.cleaned_data.get('rate')
                    if service and description and quantity and rate:
                        amount = Decimal(rate) * Decimal(quantity)
                        total += amount
                        line_item = LineItem(
                            invoice=invoice,
                            service=service,
                            description=description,
                            quantity=quantity,
                            rate=rate,
                            amount=amount
                        )
                        line_item.save()
            tax = total * Decimal('0.20')
            total_with_tax = total + tax
            invoice.total_amount = total_with_tax
            invoice.save()

            return redirect(reverse('factures:invoice-list'))
        else:
            print("Form or formset is invalid")
            print(f"Form errors: {form.errors}")
            print(f"Formset errors: {formset.errors}")

        return redirect(reverse('factures:invoice-list'))

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
    return render(request, 'factures/invoice_edit.html' if id else 'factures/invoice_create.html', context)

def view_PDF(request, id=None):
    invoice = get_object_or_404(Invoice, id=id)
    lineitem = invoice.lineitem_set.all()

    tax_rate = Decimal('0.20')
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
    return render(request, 'factures/pdf_template.html', context)

def generate_PDF(request, id):
    pdf = pdfkit.from_url(request.build_absolute_uri(reverse('factures:invoice-detail', args=[id])), False)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
    return response
