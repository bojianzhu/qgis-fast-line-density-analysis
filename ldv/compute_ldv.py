import ctypes
import os
import platform


def load_library(libname, loader_path):

    if ctypes.__version__ < '1.0.1':
        import warnings
        warnings.warn("All features of ctypes interface may not work "
                      "with ctypes < 1.0.1", stacklevel=2)

    ext = os.path.splitext(libname)[1]
    if not ext:
        # Try to load library with platform-specific name, otherwise
        # default to libname.[so|pyd].  Sometimes, these files are built
        # erroneously on non-linux platforms.
        from numpy.distutils.misc_util import get_shared_lib_extension
        so_ext = get_shared_lib_extension()
        libname_ext = [libname + so_ext]
        # mac, windows and linux >= py3.2 shared library and loadable
        # module have different extensions so try both
        so_ext2 = get_shared_lib_extension(is_python_ext=True)
        if not so_ext2 == so_ext:
            libname_ext.insert(0, libname + so_ext2)
    else:
        libname_ext = [libname]

    loader_path = os.path.abspath(loader_path)
    if not os.path.isdir(loader_path):
        libdir = os.path.dirname(loader_path)
    else:
        libdir = loader_path

    for ln in libname_ext:
        libpath = os.path.join(libdir, ln)
        if os.path.exists(libpath):
            try:
                return ctypes.cdll[libpath]
            except OSError:
                ## defective lib file
                raise
    ## if no successful return in the libname_ext loop:
    raise OSError("no file with expected extension")


dll_names = ['libldv.dll', 'libldv1.so']

ldv_C_library = None
for dll_name in dll_names:
    try:
        library_path = os.path.abspath(os.path.join(os.path.dirname(__file__), dll_name))
        ldv_C_library = load_library(dll_name, library_path)
        # ldv_C_library = ctypes.CDLL(library_path)
        break
    except Exception as e:
        pass

ldv = ldv_C_library.ldv
ldv.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_char_p))
ldv.restype = ctypes.c_char_p


def compute_ldv(args):
    args = (ctypes.c_char_p * len(args))(*args)
    result = ldv(len(args), args).decode('utf-8')
    return result
