"""Version-checked repair for the corrupt notice and its browser/timer suffix."""

import struct

import pefile


def apply_corrupt_notification_fix(data: bytes) -> bytes:
    if len(data) != 6201712:
        raise ValueError('unsupported IDM executable size')
    try:
        pe = pefile.PE(data=data, fast_load=True)
        if (pe.FILE_HEADER.Machine, pe.OPTIONAL_HEADER.Magic,
                pe.OPTIONAL_HEADER.ImageBase, pe.OPTIONAL_HEADER.SizeOfImage) != (
                0x14C, 0x10B, 0x400000, 0x5F5000):
            raise ValueError('unsupported IDM image layout')
        call = pe.get_offset_from_rva(0x850B6)
        followup = pe.get_offset_from_rva(0x850C1)
        if (call, followup) != (0x844B6, 0x844C1):
            raise ValueError('unsupported notification section layout')
        old_call = bytes.fromhex('e8b5fffeff')
        new_call = bytes.fromhex('b801000000')
        if data[call:call + 5] not in (old_call, new_call):
            raise ValueError('corrupt-notice call signature mismatch')
        if data[followup:followup + 2] not in (b'\x74\x1e', b'\x90\x90'):
            raise ValueError('repair-page branch signature mismatch')
        if data[call + 5:followup] != bytes.fromhex('83c410397d08'):
            raise ValueError('notification stack cleanup signature mismatch')
        if data[followup + 2:followup + 13] != bytes.fromhex('c78424e0010000ffffffff'):
            raise ValueError('notification exit signature mismatch')
        checksum = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    except pefile.PEFormatError as error:
        raise ValueError('invalid IDM executable') from error

    result = bytearray(data)
    result[call:call + 5] = new_call
    # Both callback arguments must take the existing cleanup/return branch.
    result[followup:followup + 2] = b'\x90\x90'
    struct.pack_into('<I', result, checksum, 0)
    value = pefile.PE(data=bytes(result), fast_load=True).generate_checksum()
    struct.pack_into('<I', result, checksum, value)
    return bytes(result)
