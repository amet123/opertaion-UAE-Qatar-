from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [l.strip() for l in f if l.strip() and not l.startswith("#")]

setup(
    name="operations_module",
    version="1.0.0",
    description="Operations Module for ERPNext 15 — Qatar/UAE Manpower & Construction",
    author="Your Company",
    author_email="admin@yourcompany.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.10",
)
