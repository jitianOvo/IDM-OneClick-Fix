import struct
import unittest

import pefile

from idmfix.notifications import apply_corrupt_notification_fix


CALL_OFFSET = 0x844B6
FOLLOWUP_OFFSET = 0x844C1


def fixture():
    data = bytearray(6201712)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3C, 0xF0)
    data[0xF0:0xF4] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0xF4, 0x14C, 1, 0, 0, 0, 0xE0, 0x102)
    optional = 0x108
    struct.pack_into('<H', data, optional, 0x10B)
    struct.pack_into('<I', data, optional + 16, 0x1000)
    struct.pack_into('<I', data, optional + 20, 0x1000)
    struct.pack_into('<I', data, optional + 28, 0x400000)
    struct.pack_into('<II', data, optional + 32, 0x1000, 0x200)
    struct.pack_into('<II', data, optional + 56, 0x5F5000, 0x400)
    struct.pack_into('<H', data, optional + 68, 2)
    struct.pack_into('<I', data, optional + 92, 16)
    section = optional + 0xE0
    data[section:section + 8] = b'.text\0\0\0'
    struct.pack_into('<IIII', data, section + 8, 0x294000, 0x1000, 0x294000, 0x400)
    struct.pack_into('<I', data, section + 36, 0x60000020)
    data[CALL_OFFSET:CALL_OFFSET + 5] = bytes.fromhex('e8b5fffeff')
    data[CALL_OFFSET + 5:FOLLOWUP_OFFSET] = bytes.fromhex('83c410397d08')
    data[FOLLOWUP_OFFSET:FOLLOWUP_OFFSET + 2] = bytes.fromhex('741e')
    data[FOLLOWUP_OFFSET + 2:FOLLOWUP_OFFSET + 13] = bytes.fromhex('c78424e0010000ffffffff')
    return bytes(data)


class NotificationTests(unittest.TestCase):
    def test_cancels_notice_and_browser_followup_without_other_changes(self):
        original = fixture()
        result = apply_corrupt_notification_fix(original)
        self.assertEqual(result[CALL_OFFSET:CALL_OFFSET + 5], bytes.fromhex('b801000000'))
        self.assertEqual(result[FOLLOWUP_OFFSET:FOLLOWUP_OFFSET + 2], b'\x90\x90')
        self.assertEqual(len(result), len(original))
        allowed = set(range(CALL_OFFSET, CALL_OFFSET + 5)) | set(range(FOLLOWUP_OFFSET, FOLLOWUP_OFFSET + 2)) | set(range(0x148, 0x14C))
        self.assertTrue(all(a == b or i in allowed for i, (a, b) in enumerate(zip(original, result))))
        self.assertTrue(pefile.PE(data=result, fast_load=True).verify_checksum())

    def test_repairs_browser_when_notice_was_already_suppressed(self):
        original = bytearray(fixture())
        original[CALL_OFFSET:CALL_OFFSET + 5] = bytes.fromhex('b801000000')
        result = apply_corrupt_notification_fix(bytes(original))
        self.assertEqual(result[FOLLOWUP_OFFSET:FOLLOWUP_OFFSET + 2], b'\x90\x90')

    def test_already_repaired_file_is_idempotent(self):
        once = apply_corrupt_notification_fix(fixture())
        self.assertEqual(apply_corrupt_notification_fix(once), once)

    def test_unknown_call_is_rejected(self):
        raw = bytearray(fixture())
        raw[CALL_OFFSET] = 0xCC
        with self.assertRaises(ValueError):
            apply_corrupt_notification_fix(bytes(raw))

    def test_unknown_followup_branch_is_rejected(self):
        raw = bytearray(fixture())
        raw[FOLLOWUP_OFFSET] = 0xEB
        with self.assertRaises(ValueError):
            apply_corrupt_notification_fix(bytes(raw))

    def test_wrong_cleanup_context_is_rejected(self):
        raw = bytearray(fixture())
        raw[FOLLOWUP_OFFSET + 2] = 0xCC
        with self.assertRaises(ValueError):
            apply_corrupt_notification_fix(bytes(raw))

    def test_changed_caller_stack_cleanup_is_rejected(self):
        raw = bytearray(fixture())
        raw[CALL_OFFSET + 7] = 0x0C
        with self.assertRaises(ValueError):
            apply_corrupt_notification_fix(bytes(raw))

    def test_wrong_architecture_is_rejected(self):
        raw = bytearray(fixture())
        struct.pack_into('<H', raw, 0xF4, 0x8664)
        with self.assertRaises(ValueError):
            apply_corrupt_notification_fix(bytes(raw))

    def test_wrong_size_or_image_layout_is_rejected(self):
        raw = bytearray(fixture())
        struct.pack_into('<I', raw, 0x108 + 28, 0x500000)
        for invalid in (bytes(raw), fixture()[:-1], b'not a PE'):
            with self.subTest(length=len(invalid)):
                with self.assertRaises(ValueError):
                    apply_corrupt_notification_fix(invalid)


if __name__ == '__main__':
    unittest.main()
