from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from nfc_cards.models import NFCCard, NFCScanLog



def nfc_vcard(request, token):
    """
    Generate a vCard (.vcf) for an active NFCCard.
    """
    card = get_object_or_404(NFCCard, qr_token=token, is_active=True)
    officer = card.profile.user
    profile = card.profile

    # Build vCard lines safely, skipping empty fields
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{officer.get_full_name()}",
        f"N:{officer.lastname};{officer.firstname};;;",
    ]

    if officer.phone:  # adjust field name if different
        vcard_lines.append(f"TEL;TYPE=CELL:{officer.phone}")

    if officer.email:
        vcard_lines.append(f"EMAIL:{officer.email}")

    if profile.station:
        vcard_lines.append(f"ORG:{profile.station}")

    vcard_lines.append("END:VCARD")

    vcard_content = "\r\n".join(vcard_lines)

    response = HttpResponse(vcard_content, content_type='text/vcard')
    response['Content-Disposition'] = f'attachment; filename="{officer.staffid}.vcf"'
    return response


def nfc_scan_logs(request, staffid=None):
    """
    Display NFC scan logs.
    - If staffid is provided, filter logs for that officer only.
    - Otherwise, show all logs.
    """
    if staffid:
        # Filter logs for a specific officer
        card = get_object_or_404(NFCCard, profile__user__staffid=staffid)
        logs = NFCScanLog.objects.filter(nfc_card=card).select_related('nfc_card', 'nfc_card__profile', 'nfc_card__profile__user')
    else:
        # Show all logs
        logs = NFCScanLog.objects.select_related('nfc_card', 'nfc_card__profile', 'nfc_card__profile__user')

    # Order logs by most recent
    logs = logs.order_by('-scanned_at')

    context = {
        'logs': logs,
        'staffid': staffid,
    }
    return render(request, 'nfc_cards/scan_logs.html', context)