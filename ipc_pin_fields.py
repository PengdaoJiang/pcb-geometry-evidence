"""Observed fixed-column pin identity for retained ZCU111 IPC-D-356A records.

Use columns 21-26 reference, 27 separator, 28-31 pin (one-based).
Column 32 is separate, observed blank/M; it is not part of the pin identifier.
This module does not reinterpret connectivity/testpoint flags or repair truncation.
"""
import re

def named_pin_fields(raw):
    if len(raw)<32 or raw[:3] not in ('307','317','327'):raise ValueError('Unqualified IPC record')
    if raw[26]!='-':raise ValueError('No named-pin separator')
    reference=raw[20:26].strip();pin=raw[27:31].strip();marker=raw[31]
    if not reference or not pin or not re.fullmatch(r'\S+',reference) or not re.fullmatch(r'\S+',pin):
        raise ValueError('Empty or space-containing pin identity')
    if marker not in (' ','M'):raise ValueError('Unqualified adjacent flag')
    return dict(pin=reference+'.'+pin,reference=reference,number=pin,adjacent_flag=marker)
