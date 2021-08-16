from setuptools import setup, find_packages
from mezzanine_agenda import __version__
import subprocess


def get_long_desc():
    """Use Pandoc to convert the readme to ReST for the PyPI."""
    try:
        return subprocess.check_output(
            ['pandoc', '-f', 'markdown', '-t', 'rst', 'README.mdown']
        )
    except Exception:
        print("WARNING: The long readme wasn't converted properly")


setup(
    name='mezzanine-agenda',
    version=__version__,
    description='Events for the Mezzanine CMS',
    long_description=str(get_long_desc()),
    author='James Pells',
    author_email='jimmy@jamespells.com',
    url='https://github.com/jpells/mezzanine-agenda',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        "icalendar==4.0.3",
        "geopy==1.17.0",
        "pytz==2018.7",
        "django-autocomplete-light>=3.2.1",
    ]
)
