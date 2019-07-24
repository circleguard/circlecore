import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="circleguard",
    version="2.0",
    author="Liam DeVoe, Samuel",
    author_email="orionldevoe@gmail.com",
    description="A player made and maintained cheat detection tool for osu!. "
                "Provides support for detecting replay stealing and remodding "
                "from a profile, map, or set of osr files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/circleguard/circlecore",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "circleparse",
        "numpy",
        "wtc",
        "requests",
        "ossapi"
    ]
)
