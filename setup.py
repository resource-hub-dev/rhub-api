# based on https://github.com/pypa/sampleproject

import pathlib

from setuptools import find_packages, setup


here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="rhub",
    version="0.0.1",
    description="Resource Hub API/backend service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/resource-hub-dev/rhub-api",
    author="Red Hat, inc.",
    author_email="resource-hub-dev@redhat.com",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7, <4",
    install_requires=[
        "alembic",
        "ansible",
        "attrs",
        "celery",
        "click",
        "coloredlogs",
        "connexion[swagger-ui] ~= 2.14",
        "cron-validator >= 1.0.5",
        "dpath",
        "dynaconf",
        "flask",
        "flask-apscheduler",
        "flask-cors",
        "flask-dotenv",
        "flask_injector",
        "flask-migrate",
        "flask-sqlalchemy ~= 2.5",
        "gunicorn",
        "hvac",
        "injector",
        "inotify",
        "jinja2",
        "kombu",
        "ldap3",
        "oic",
        "openapi_spec_validator",
        "openstacksdk",
        "prance[osv]",
        "prometheus_flask_exporter",
        "psycopg2-binary",
        "python-dateutil",
        "python-ironicclient",
        "pyyaml",
        "requests",
        "SQLAlchemy ~= 1.4",
        "tenacity",
        "Werkzeug",
    ],
    extras_require={
        "dev": [
            "build",
            "check-manifest>=0.42",
            "coverage",
            "pip-tools",
            "tox >= 4",
        ],
    },
    classifiers=[
        'License :: OSI Approved :: MIT License',
    ],
)
