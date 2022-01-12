from distutils.core import setup
from setuptools import find_packages
import re

with open("README.md", "r") as readme:
    long_description = readme.read()

# https://stackoverflow.com/a/7071358
VERSION = "Unknown"
VERSION_RE = r"^__version__ = ['\"]([^'\"]*)['\"]"

with open("circleguard/version.py") as f:
    match = re.search(VERSION_RE, f.read())
    if match:
        VERSION = match.group(1)
    else:
        raise RuntimeError("Unable to find version string in circleguard/version.py")

setup(
    name="circleguard",
    version=VERSION,
    description="A utilities library for osu!. Provides support for parsing "
        "replays from a file or from the api, as well as support for unstable "
        "rate, hits, similarity, and frametime calculations.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    keywords = ["osu!, python, cheat-detection, replay-stealing, remodding"],
    author="Liam DeVoe",
    author_email="orionldevoe@gmail.com",
    url="https://github.com/circleguard/circlecore",
    download_url = "https://github.com/circleguard/circlecore/tarball/v" + VERSION,
    packages=find_packages(),
    install_requires=[
        "osrparse~=6.0",
        "ossapi~=2.1",
        "wtc==1.2.1",
        "numpy",
        "requests",
        "slider>=0.5.1",
        "scipy"
    ],
    extras_require={
        "graphing": [
            "matplotlib"
        ]
    }
)
