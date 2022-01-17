from setuptools import setup, find_packages
from mezzanine_agenda import __version__
import subprocess

setup(name='mezzanine-agenda',
    version=__version__,
    description='Events for the Mezzanine CMS',
    author='James Pells',
    author_email='jimmy@jamespells.com',
    url='https://github.com/jpells/mezzanine-agenda',
    packages=find_packages(),
    include_package_data=True,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        "icalendar",
        "geopy",
        "pytz",
        "django-autocomplete-light==3.8.2",
    ]
)
