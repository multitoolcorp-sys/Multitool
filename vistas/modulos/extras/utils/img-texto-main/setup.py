from setuptools import setup
from constantes import Configuracion as conf

setup(
    name = conf.NOMBRE_AP,
    version = conf.VERSION,
    packages = [''],
    install_requires=[
        'pytesseract',
        'python-gettext',              
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: GNU GENERAL PUBLIC LICENSE V3',
        'Operating System :: OS Independent',
    ],
    description=conf.DESCRIPCION_AP,
    url='https://github.com/medinaccesar/img-texto'
)
