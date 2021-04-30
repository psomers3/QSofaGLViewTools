from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="QSofaGLViewTools",
    version="0.0.1",
    author="Peter Somers",
    author_email="peter.somers@isys.uni-stuttgart.de",
    description="A small PyQt widget library for viewing SOFA simulation cameras",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/psomers3/QSofaGLViewTools.git",
    packages=['QSofaGLViewTools'],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3',
    install_requires=['numpy',
                      'qtpy',
                      'scipy',
                      'pyopengl',
                      'inputs']
)
