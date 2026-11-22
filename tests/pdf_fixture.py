"""PDF mínimo válido de dos páginas con texto distinguible."""

def pdf_fixture():
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    def flujo(linea):
        texto = b"BT /F1 12 Tf 20 50 Td (" + linea + b") Tj ET"
        return f"<< /Length {len(texto)} >>\nstream\n".encode() + texto + b"\nendstream"
    objetos.extend([flujo(b"Informe Cerebro"),
                    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
                    flujo(b"Pruebas de energia solar")])
    bruto = b"%PDF-1.4\n"
    offsets = []
    for numero, objeto in enumerate(objetos, 1):
        offsets.append(len(bruto))
        bruto += f"{numero} 0 obj\n".encode() + objeto + b"\nendobj\n"
    inicio = len(bruto)
    bruto += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        bruto += f"{offset:010d} 00000 n \n".encode()
    return bruto + f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio}\n%%EOF\n".encode()
