#!/usr/bin/env python3
"""
Cifra datos/ofertas.json en datos/ofertas.enc para que solo la página de miembros pueda leerlo.

Usa una clave pública (datos/clave_publica.pem, que puede estar a la vista). La clave privada,
que es la única que permite descifrar, vive solo en Vercel. Formato:
  {"v": 1, "k": clave AES cifrada con RSA-OAEP-SHA256, "n": nonce, "d": datos gzip cifrados con AES-256-GCM}
"""
import base64
import gzip
import json
import os
import sys

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA = os.path.join(RAIZ, "datos", "ofertas.json")
SALIDA = os.path.join(RAIZ, "datos", "ofertas.enc")
CLAVE = os.path.join(RAIZ, "datos", "clave_publica.pem")


def cifrar(texto: bytes, publica_pem: bytes) -> dict:
    publica = serialization.load_pem_public_key(publica_pem)
    clave = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    datos = AESGCM(clave).encrypt(nonce, gzip.compress(texto), None)
    clave_cifrada = publica.encrypt(clave, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "k": b64(clave_cifrada), "n": b64(nonce), "d": b64(datos)}


def main():
    if not os.path.exists(ENTRADA):
        print("No hay ofertas nuevas que cifrar.")
        return 0
    with open(ENTRADA, "rb") as f:
        texto = f.read()
    with open(CLAVE, "rb") as f:
        sobre = cifrar(texto, f.read())
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(sobre, f)
    print(f"Cifrado: {len(texto):,} bytes → {os.path.getsize(SALIDA):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
