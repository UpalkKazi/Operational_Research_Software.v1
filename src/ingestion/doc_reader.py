"""Plain-text extraction from legacy Word 97-2003 ``.doc`` files.

Implements the piece-table lookup described in [MS-DOC] §2.4.1 using
``olefile`` only, so no system tools (antiword, LibreOffice) are needed.
"""

from __future__ import annotations

import io
import re
import struct


class DocReadError(ValueError):
    pass


def extract_doc_text(data: bytes) -> str:
    try:
        import olefile
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise DocReadError("Reading .doc files needs the 'olefile' package (pip install olefile).") from exc

    if not olefile.isOleFile(io.BytesIO(data)):
        if data[:4] == b"PK\x03\x04":
            raise DocReadError("This file is a .docx saved with a .doc extension; rename it to .docx.")
        if data.lstrip()[:5] == b"{\\rtf":
            raise DocReadError("This file is RTF saved with a .doc extension; save it as .docx or .txt.")
        raise DocReadError("Not a Word 97-2003 document (missing OLE header).")

    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        if not ole.exists("WordDocument"):
            raise DocReadError("The file has no WordDocument stream.")
        word = ole.openstream("WordDocument").read()
        if len(word) < 0x200 or struct.unpack_from("<H", word, 0)[0] != 0xA5EC:
            raise DocReadError("Unrecognised Word document header.")
        flags = struct.unpack_from("<H", word, 0x0A)[0]
        if flags & 0x0100:
            raise DocReadError("The document is encrypted or password protected.")
        table_name = "1Table" if flags & 0x0200 else "0Table"
        if not ole.exists(table_name):
            raise DocReadError(f"The document is missing its {table_name} stream.")
        table = ole.openstream(table_name).read()

        position = 32
        csw = struct.unpack_from("<H", word, position)[0]
        position += 2 + csw * 2
        cslw = struct.unpack_from("<H", word, position)[0]
        position += 2 + cslw * 4
        position += 2  # cbRgFcLcb
        fc_clx, lcb_clx = struct.unpack_from("<II", word, position + 33 * 8)
        if lcb_clx == 0 or fc_clx + lcb_clx > len(table):
            raise DocReadError("The document's text table could not be located.")
        clx = table[fc_clx:fc_clx + lcb_clx]

        index = 0
        plc = b""
        while index < len(clx):
            marker = clx[index]
            if marker == 0x01:
                size = struct.unpack_from("<H", clx, index + 1)[0]
                index += 3 + size
            elif marker == 0x02:
                size = struct.unpack_from("<I", clx, index + 1)[0]
                plc = clx[index + 5:index + 5 + size]
                break
            else:
                raise DocReadError("Corrupt piece table in the document.")
        if not plc:
            raise DocReadError("The document has no text pieces.")

        count = (len(plc) - 4) // 12
        cps = struct.unpack_from(f"<{count + 1}I", plc, 0)
        parts = []
        for i in range(count):
            descriptor = plc[(count + 1) * 4 + i * 8:(count + 1) * 4 + (i + 1) * 8]
            fc_value = struct.unpack_from("<I", descriptor, 2)[0]
            chars = cps[i + 1] - cps[i]
            if fc_value & 0x40000000:
                offset = (fc_value & 0x3FFFFFFF) // 2
                parts.append(word[offset:offset + chars].decode("cp1252", errors="replace"))
            else:
                offset = fc_value & 0x3FFFFFFF
                parts.append(word[offset:offset + 2 * chars].decode("utf-16-le", errors="replace"))
        text = "".join(parts)
    finally:
        ole.close()

    text = re.sub("\x13[^\x13\x14\x15]*\x14", "", text)
    text = re.sub("[\x13\x14\x15]", "", text)
    text = text.replace("\r", "\n").replace("\x0b", "\n").replace("\x0c", "\n").replace("\x07", "\t")
    text = re.sub(r"[\x00-\x08\x0e-\x1f]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
