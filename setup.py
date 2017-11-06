from distutils.core import setup
from setuptools import find_packages
from pathlib import Path


def get_requirements():
    with open("requirements.txt", "r") as f:
        requirements = f.readlines()
    requirements.append("red-discordbot>=3.0.0b1")
    return requirements


def find_data_folders():
    def glob_data_files(path: Path):
        data = path.glob("*")
        parents = path.parents
        return [str(d.relative_to(parents[0])) for d in data]

    ret = {}
    cogs_path = Path("palmtree5-cogs")

    for cog_folder in cogs_path.iterdir():
        data_folder = cog_folder / "data"
        if not data_folder.is_dir():
            continue

        pkg_name = str(cog_folder).replace("/", ".")
        ret[pkg_name] = glob_data_files(data_folder)
    return ret


setup(
    name='palmtree5-cogs',
    version='3.0.0a1',
    packages=find_packages(include=["palmtree5-cogs", "palmtree5-cogs.*"]),
    package_data=find_data_folders(),
    url='https://github.com/palmtree5/palmtree5-cogs',
    license='GPLv3',
    author='palmtree5',
    author_email='',
    description='Some extensions for Red-DiscordBot',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Communications :: Chat'
    ],
    python_requires='>=3.5',
    setup_requires=get_requirements(),
    install_requires=get_requirements()
)
