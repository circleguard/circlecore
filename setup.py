import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="circleguard",
    version="2.0",
    author="Liam DeVoe, Travis Smith, Samuel xx",
    author_email="orionldevoe@gmail.com, xxxx, xxxx",
    description="Detect cheaters from replay files, leaderboards, or profiles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/circleguard/circlecore",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
