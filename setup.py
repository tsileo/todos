from setuptools import setup

setup(
    name="todos",
    version="0.1.0",
    py_modules=["todos"],
    install_requires=[
        "pyyaml",
        "blobstash @  git+ssh://git@github.com/tsileo/blobstash-python",
    ],
    entry_points={"console_scripts": ["todos = todos:main"]},
)
