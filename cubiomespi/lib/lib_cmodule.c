#define PY_SSIZE_T_CLEAN
#include <Python.h>

PyMODINIT_FUNC PyInit_lib_c(void)
{
    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "lib_c",
        "Vendored cubiomes native library",
        -1,
        NULL,
    };
    return PyModule_Create(&moduledef);
}
