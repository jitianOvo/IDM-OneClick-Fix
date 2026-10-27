"""Version-checked notification repair that preserves PE base relocations."""

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
        gate_rva = 0x9BB78
        gate = pe.get_offset_from_rva(gate_rva)
        download = pe.get_offset_from_rva(gate_rva + 9)
        if (call, followup, gate, download) != (0x844B6, 0x844C1, 0x9AF78, 0x9AF81):
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
        original_gate = bytes.fromhex('833da093780000740d')
        if data[gate:download] not in (original_gate, b'\x90' * 9):
            raise ValueError('download gate signature mismatch')
        if data[download:download + 5] not in (bytes.fromhex('e89ad20000'), new_call):
            raise ValueError('download-notice call signature mismatch')
        if data[gate - 9:gate] != bytes.fromhex('f68684000000087516'):
            raise ValueError('download caller flags signature mismatch')
        if data[download + 5:download + 19] != bytes.fromhex('85c00f840f0100008b8e84000000'):
            raise ValueError('download continuation signature mismatch')
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_BASERELOC']])
        relocations = [entry for block in getattr(pe, 'DIRECTORY_ENTRY_BASERELOC', [])
                       for entry in block.entries if entry.type]
        gate_relocations = [(entry.rva, entry.type) for entry in relocations
                            if gate_rva <= entry.rva < gate_rva + 14]
        if gate_relocations != [(gate_rva + 2, 3)]:
            raise ValueError('download gate relocation mismatch')
        if any(0x850B6 <= entry.rva < 0x850BB or 0x850C1 <= entry.rva < 0x850C3
               for entry in relocations):
            raise ValueError('unexpected notification relocation')
        checksum = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    except pefile.PEFormatError as error:
        raise ValueError('invalid IDM executable') from error

    result = bytearray(data)
    result[call:call + 5] = new_call
    # Both callback arguments must take the existing cleanup/return branch.
    result[followup:followup + 2] = b'\x90\x90'
    # The operand retains a HIGHLOW relocation; NOPs here become invalid at load time.
    result[gate:download] = original_gate
    result[download:download + 5] = new_call
    struct.pack_into('<I', result, checksum, 0)
    value = pefile.PE(data=bytes(result), fast_load=True).generate_checksum()
    struct.pack_into('<I', result, checksum, value)
    return bytes(result)
