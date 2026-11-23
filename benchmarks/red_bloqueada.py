"""Ejecuta una prueba Linux bajo un filtro seccomp que solo permite sockets Unix."""
import ctypes as C
import errno
import os
import socket
import sys


class Comparacion(C.Structure):
    _fields_ = [("arg", C.c_uint), ("op", C.c_int),
                ("dato_a", C.c_uint64), ("dato_b", C.c_uint64)]


def bloquear():
    # El filtro se hereda al hacer exec y al lanzar el instalador o llama.cpp.
    biblioteca = C.CDLL("libseccomp.so.2")
    biblioteca.seccomp_init.argtypes = [C.c_uint32]
    biblioteca.seccomp_init.restype = C.c_void_p
    biblioteca.seccomp_syscall_resolve_name.argtypes = [C.c_char_p]
    biblioteca.seccomp_rule_add_array.argtypes = [C.c_void_p, C.c_uint32, C.c_int,
                                                 C.c_uint, C.POINTER(Comparacion)]
    biblioteca.seccomp_load.argtypes = [C.c_void_p]
    biblioteca.seccomp_release.argtypes = [C.c_void_p]
    contexto = biblioteca.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not contexto:
        raise RuntimeError("No se pudo iniciar libseccomp.")
    try:
        denegar = 0x00050000 | errno.EAFNOSUPPORT  # SCMP_ACT_ERRNO
        comparacion = Comparacion(0, 1, socket.AF_UNIX, 0)  # SCMP_CMP_NE
        for nombre in (b"socket", b"socketpair", b"io_uring_setup"):
            llamada = biblioteca.seccomp_syscall_resolve_name(nombre)
            if llamada < 0:
                raise RuntimeError(f"No se pudo resolver {nombre.decode()}.")
            cantidad = 0 if nombre == b"io_uring_setup" else 1
            filtros = C.byref(comparacion) if cantidad else None
            if biblioteca.seccomp_rule_add_array(contexto, denegar, llamada, cantidad, filtros):
                raise RuntimeError(f"No se pudo filtrar {nombre.decode()}.")
        if biblioteca.seccomp_load(contexto):
            raise RuntimeError("El kernel no aceptó el filtro seccomp.")
    finally:
        biblioteca.seccomp_release(contexto)
    for familia in (socket.AF_INET, socket.AF_INET6):
        for tipo in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            try:
                with socket.socket(familia, tipo):
                    raise RuntimeError("El kernel permitió abrir un socket IP.")
            except OSError as error:
                if error.errno != errno.EAFNOSUPPORT:
                    raise
    with socket.socket(socket.AF_UNIX):
        pass


def main():
    if len(sys.argv) < 2 or not sys.platform.startswith("linux"):
        raise SystemExit("Uso en Linux: python -m benchmarks.red_bloqueada COMANDO ARGUMENTOS")
    bloquear()
    print("Filtro seccomp activo: TCP/UDP IPv4 e IPv6 bloqueados; AF_UNIX disponible.", file=sys.stderr)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
