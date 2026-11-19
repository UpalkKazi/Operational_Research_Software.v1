"""
File Parser — extract structured data and raw text from uploaded files.

Supported formats: Excel (.xlsx/.xls), CSV, Word (.docx/.doc),
plain text (.txt), PDF, and MPS (.mps/.mps.gz).
"""

import gzip
import io
import warnings
from pathlib import Path
from typing import Any, Dict, List, Union


class FileParser:
    """
    Parse uploaded files into a structured dict that always includes a
    ``raw_text`` key containing a plain-text representation of the full
    content (suitable for passing to the AI classifier).
    """

    _EXT_HANDLERS = {
        '.xlsx': '_parse_excel',
        '.xls': '_parse_xls',
        '.csv': '_parse_csv',
        '.docx': '_parse_docx',
        '.doc': '_parse_doc',
        '.txt': '_parse_text',
        '.pdf': '_parse_pdf',
        '.mps': '_parse_mps',
        '.mps.gz': '_parse_mps',
    }

    def parse(
        self,
        file_path_or_bytes: Union[str, Path, bytes, io.BytesIO],
        filename: str = '',
    ) -> Dict[str, Any]:
        """
        Detect file type and extract content.

        Args:
            file_path_or_bytes: A file path (str/Path) **or** raw bytes /
                BytesIO (e.g. from ``st.file_uploader``).
            filename: Original filename — used for extension detection when
                *file_path_or_bytes* is bytes.

        Returns:
            A dict that **always** contains at least ``type``, ``raw_text``,
            and (on failure) ``error``.
        """
        try:
            ext = self._detect_extension(file_path_or_bytes, filename)
            handler_name = self._EXT_HANDLERS.get(ext)
            if not handler_name:
                return {
                    'type': 'error',
                    'raw_text': '',
                    'error': (
                        f"Unsupported file type '{ext}'. "
                        f"Supported: {', '.join(sorted(self._EXT_HANDLERS))}"
                    ),
                }

            data = self._to_bytes(file_path_or_bytes)
            if ext.endswith('.gz'):
                from src.ingestion.mps_reader import decompress_limited
                data = decompress_limited(data)
            handler = getattr(self, handler_name)
            result = handler(data, filename)

            if 'raw_text' not in result:
                result['raw_text'] = self._build_raw_text(result)

            if isinstance(file_path_or_bytes, (str, Path)):
                result['file_path'] = str(file_path_or_bytes)

            return result

        except Exception as e:
            return {'type': 'error', 'raw_text': '', 'error': str(e)}

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_extension(
        source: Union[str, Path, bytes, io.BytesIO],
        filename: str,
    ) -> str:
        name = ''
        if filename:
            name = filename
        elif isinstance(source, (str, Path)):
            name = str(source)

        if not name:
            return ''

        low = name.lower()
        if low.endswith('.mps.gz'):
            return '.mps.gz'
        return Path(low).suffix

    @staticmethod
    def _to_bytes(source: Union[str, Path, bytes, io.BytesIO]) -> bytes:
        if isinstance(source, bytes):
            return source
        if isinstance(source, io.BytesIO):
            source.seek(0)
            return source.read()
        with open(source, 'rb') as f:
            return f.read()

    # ------------------------------------------------------------------
    #  Raw-text builder (fallback when handler doesn't set raw_text)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_raw_text(result: Dict[str, Any]) -> str:
        rtype = result.get('type', '')

        if rtype == 'excel':
            parts: List[str] = []
            for sheet in result.get('sheets', []):
                parts.append(f"--- Sheet: {sheet['name']} ---")
                headers = sheet.get('headers', [])
                if headers:
                    parts.append('\t'.join(str(h) for h in headers))
                for row in sheet.get('rows', []):
                    parts.append(
                        '\t'.join(str(row.get(h, '')) for h in headers)
                    )
            return '\n'.join(parts)

        if rtype == 'csv':
            sheets = result.get('sheets', [])
            if sheets:
                sheet = sheets[0]
                headers = sheet.get('headers', [])
                lines = ['\t'.join(str(h) for h in headers)]
                for row in sheet.get('rows', []):
                    lines.append(
                        '\t'.join(str(row.get(h, '')) for h in headers)
                    )
                return '\n'.join(lines)
            return ''

        if rtype == 'docx':
            parts = list(result.get('paragraphs', []))
            for table in result.get('tables', []):
                for row in table:
                    parts.append('\t'.join(str(c) for c in row))
            return '\n'.join(parts)

        if rtype == 'text':
            return result.get('content', '')

        if rtype == 'pdf':
            return '\n\n'.join(result.get('pages', []))

        return ''

    # ------------------------------------------------------------------
    #  Format-specific parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_excel(data: bytes, filename: str) -> Dict[str, Any]:
        import openpyxl

        wb = openpyxl.load_workbook(
            io.BytesIO(data), read_only=True, data_only=True,
        )
        sheets: List[Dict[str, Any]] = []
        for name in wb.sheetnames:
            ws = wb[name]
            rows_iter = ws.iter_rows(values_only=True)

            first_row = next(rows_iter, None)
            if first_row is None:
                sheets.append({'name': name, 'headers': [], 'rows': []})
                continue

            headers = [
                str(c) if c is not None else f'col_{i}'
                for i, c in enumerate(first_row)
            ]
            data_rows = [
                {headers[i]: cell for i, cell in enumerate(row)}
                for row in rows_iter
            ]
            sheets.append({
                'name': name,
                'headers': headers,
                'rows': data_rows,
            })

        wb.close()
        return {'type': 'excel', 'sheets': sheets}

    @staticmethod
    def _parse_xls(data: bytes, filename: str) -> Dict[str, Any]:
        try:
            import xlrd
        except ImportError as exc:
            raise ImportError("Reading .xls files needs 'xlrd' (pip install xlrd).") from exc

        book = xlrd.open_workbook(file_contents=data)
        sheets: List[Dict[str, Any]] = []
        for sheet in book.sheets():
            if sheet.nrows == 0:
                sheets.append({'name': sheet.name, 'headers': [], 'rows': []})
                continue
            headers = [
                str(c) if c not in (None, '') else f'col_{i}'
                for i, c in enumerate(sheet.row_values(0))
            ]
            rows = [
                {headers[i]: cell for i, cell in enumerate(sheet.row_values(r))}
                for r in range(1, sheet.nrows)
            ]
            sheets.append({'name': sheet.name, 'headers': headers, 'rows': rows})
        return {'type': 'excel', 'sheets': sheets}

    @staticmethod
    def _parse_doc(data: bytes, filename: str) -> Dict[str, Any]:
        from src.ingestion.doc_reader import extract_doc_text

        text = extract_doc_text(data)
        paragraphs = [p for p in text.split('\n') if p.strip()]
        return {'type': 'docx', 'paragraphs': paragraphs, 'tables': [], 'raw_text': text}

    @staticmethod
    def _parse_csv(data: bytes, filename: str) -> Dict[str, Any]:
        import pandas as pd

        text = data.decode('utf-8', errors='replace')
        df = pd.read_csv(io.StringIO(text))
        headers = list(df.columns)
        rows = df.to_dict(orient='records')
        return {
            'type': 'csv',
            'sheets': [{'name': 'Sheet1', 'headers': headers, 'rows': rows}],
        }

    @staticmethod
    def _parse_docx(data: bytes, filename: str) -> Dict[str, Any]:
        import docx

        doc = docx.Document(io.BytesIO(data))

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        tables: List[List[List[str]]] = []
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                table_data.append([cell.text for cell in row.cells])
            tables.append(table_data)

        return {'type': 'docx', 'paragraphs': paragraphs, 'tables': tables}

    @staticmethod
    def _parse_text(data: bytes, filename: str) -> Dict[str, Any]:
        content = data.decode('utf-8', errors='replace')
        return {'type': 'text', 'content': content, 'raw_text': content}

    @staticmethod
    def _parse_pdf(data: bytes, filename: str) -> Dict[str, Any]:
        pages: List[str] = []

        # Tier 1: PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(stream=data, filetype='pdf')
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            return {'type': 'pdf', 'pages': pages}
        except ImportError:
            pass

        # Tier 2: pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    pages.append(text)
            return {'type': 'pdf', 'pages': pages}
        except ImportError:
            pass

        raise ImportError(
            "No PDF library available. Install one of: "
            "PyMuPDF (pip install pymupdf) or pdfplumber (pip install pdfplumber)"
        )

    # ------------------------------------------------------------------
    #  MPS (Mathematical Programming System) format
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_mps(data: bytes, filename: str) -> Dict[str, Any]:
        """Parse MPS through the canonical reader (RANGES, OBJSENSE, bounds)."""
        from src.ingestion.mps_reader import read_mps_bytes

        spec = read_mps_bytes(data, filename='')
        variable_bounds: Dict[str, Dict[str, Any]] = {
            v.name: {'lb': v.lower_bound, 'ub': v.upper_bound, 'type': v.variable_type}
            for v in spec.variables
        }
        constraint_list = [
            {
                'name': c.name,
                'type': c.sense,
                'coefficients': dict(c.expression.coefficients),
                'rhs': c.rhs,
            }
            for c in spec.constraints
        ]
        stats = spec.stats()
        type_desc = [
            f"{stats[k]} {k}" for k in ('continuous', 'integer', 'binary') if stats[k]
        ]
        parts: List[str] = [
            f"MPS Problem: {spec.name or '(unnamed)'}",
            f"Variables: {stats['variables']} ({', '.join(type_desc)})",
            f"Constraints: {stats['constraints']}",
            f"Objective: {spec.objective.sense} {spec.objective.name}",
        ]
        obj = list(spec.objective.expression.coefficients.items())
        if obj:
            suffix = ', ...' if len(obj) > 10 else ''
            parts.append(
                "Objective coefficients: "
                + ', '.join(f"{v}={c}" for v, c in obj[:10]) + suffix
            )
        if constraint_list:
            parts.append("Constraints summary:")
            for con in constraint_list[:5]:
                parts.append(f"  {con['name']} ({con['type']}): rhs={con['rhs']}")
            if len(constraint_list) > 5:
                parts.append(f"  ... ({len(constraint_list) - 5} more)")

        return {
            'type': 'mps',
            'name': spec.name,
            'objective_name': spec.objective.name,
            'objective_sense': spec.objective.sense,
            'objective_constant': spec.objective.expression.constant,
            'variables': [v.name for v in spec.variables],
            'variable_bounds': variable_bounds,
            'constraints': constraint_list,
            'objective_coefficients': dict(spec.objective.expression.coefficients),
            'num_variables': stats['variables'],
            'num_constraints': stats['constraints'],
            'raw_text': '\n'.join(parts),
            'model_spec': spec,
        }
