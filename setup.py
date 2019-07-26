from distutils.core import setup
from setuptools import find_packages
from circleguard.__init__ import __version__

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="circleguard",
    version=__version__,
    description="A player made and maintained cheat detection tool for osu!. "
                "Provides support for detecting replay stealing and remodding "
                "from a profile, map, or set of osr files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords = ["osu!, python, cheat-detection, replay-stealing, remodding"],
    author="Liam DeVoe",
    author_email="orionldevoe@gmail.com",
    url="https://github.com/circleguard/circlecore",
    download_url = "https://github.com/circleguard/circlecore/tarball/v" + __version__,
    license = "MIT",
    packages=find_packages(),
    install_requires=[
        "circleparse >= 5.0.1",
        "ossapi >= 1.2.0",
        "wtc >= 1.1.3",
        "numpy",
        "requests"
    ]
)
