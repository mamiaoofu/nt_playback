import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.core.model.authorize.models import UserFileShare
from apps.core.model.audio.models import AudioInfo
from django.db.models import Q

tokens = ['nichetel']
for tok in tokens:
    lower = tok.lower()
    base_tok_q = (
        Q(create_by__username__icontains=tok) |
        Q(create_by__first_name__icontains=tok) |
        Q(create_by__last_name__icontains=tok) |
        Q(code__icontains=tok) |
        Q(email__icontains=tok) |
        Q(description__icontains=tok)
    )

    ids = list(AudioInfo.objects.filter(audiofile__file_name__icontains=tok).distinct().values_list('audiofile__id', flat=True)[:100])
    
    if ids:
        audio_q = Q()
        for aid in ids:
            audio_q |= Q(audiofile_id__icontains=f'"{aid}"')
        base_tok_q |= audio_q

    qs = UserFileShare.objects.filter(type='ticket').filter(base_tok_q)
    print(f"Total found: {qs.count()}")
    for ticket in qs[:10]:
        print(f"Ticket ID: {ticket.id}, Code: {ticket.code}")
        print(f"  create_by__username: {ticket.create_by.username if ticket.create_by else None}")
        print(f"  create_by__first_name: {ticket.create_by.first_name if ticket.create_by else None}")
        print(f"  create_by__last_name: {ticket.create_by.last_name if ticket.create_by else None}")
        print(f"  email: {ticket.email}")
        print(f"  description: {ticket.description}")
        print(f"  audiofile_id: {ticket.audiofile_id}")
        if ids:
            print(f"  matches audio IDs: {ids}")
