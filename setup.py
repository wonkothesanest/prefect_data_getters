from setuptools import setup, find_packages

setup(
    name="agentic_ai",
    version="0.1",
    description="Source code for trying to automate tedious parts of being a manager. So that I can be a better boss and invest heavily in my people.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
