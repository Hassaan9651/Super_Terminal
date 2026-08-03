"""Compatibility installer for older versions of pip and setuptools.

This is the canonical package metadata. Ubuntu releases can ship an older pip
that cannot read PEP 621 metadata for ``pip install -e .``; defining metadata
here keeps both legacy and modern editable installs from becoming
``UNKNOWN-0.0.0``.
"""

from setuptools import setup


setup(
    name="superterminal-cli",
    version="1.0.3",
    description="Natural-language terminal command translator with editable safety prompts.",
    python_requires=">=3.10",
    py_modules=["main"],
    packages=["utils"],
    install_requires=[
        "google-genai>=1.0.0,<2.0.0",
        "prompt-toolkit>=3.0.0,<4.0.0",
        "python-dotenv>=1.0.0,<2.0.0",
    ],
    extras_require={"dev": ["pytest>=8.0.0,<9.0.0"]},
    entry_points={
        "console_scripts": [
            "superterminal=main:main",
            "super=main:main",
        ]
    },
)
