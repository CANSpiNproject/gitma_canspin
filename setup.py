import setuptools
import os
from gitma_canspin import __version__

this_dir = os.path.dirname(os.path.realpath(__file__))

setuptools.setup(
    name="gitma_canspin",
    version=__version__,
    author="CANSpiN project",
    packages=setuptools.find_packages(),
    description="gitma 2.0.1 fork for project specific needs of the CANSpiN project",
    long_description=open(os.path.join(this_dir, "README.md")).read(),
    long_description_content_type="text/markdown",
    url="https://cls-gitlab.phil.uni-wuerzburg.de/canspin/gitma-canspin",
    entry_points={ "console_scripts": ["gui-start=gitma_canspin.scripts.gitma_CANSpiN:run"] },
    python_requires="==3.10.*",
    install_requires=open(os.path.join(this_dir, "requirements.txt")).read().split("\n")
)
