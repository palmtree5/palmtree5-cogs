from distutils.core import setup
from setuptools import find_packages
from pathlib import Path


def get_requirements():
    with open("requirements.txt", "r") as f:
        requirements = f.readlines()
    requirements.append("red-discordbot>=3.0.0b1")
    return requirements


def find_data_folders():
    """
    Something similar to what is used for finding translations in the Red v3 repo
    but for data files instead. It happens to work
    :return:
    """
    def glob_locale_files(path: Path):
        msgs = path.glob("*.po")
        parents = path.parents
        return [str(m.relative_to(parents[0])) for m in msgs]

    def glob_data_files(path: Path):
        data = path.glob("*")
        parents = path.parents
        return [str(d.relative_to(parents[0])) for d in data]

    ret = {}
    cogs_path = Path("palmtree5-cogs")

    for cog_folder in cogs_path.iterdir():
        data_folder = cog_folder / "data"
        locale_folder = cog_folder / "locales"
        if not data_folder.is_dir() and not locale_folder.is_dir():
            continue

        pkg_name = str(cog_folder).replace("/", ".")

        # both of these should be at least empty lists because PEP 448 usage
        data_files = []
        locale_files = []
        if data_folder.is_dir():
            data_files = glob_data_files(data_folder)
        if locale_folder.is_dir():
            locale_files = glob_locale_files(locale_folder)
        combined_data_and_locale = [*data_files, *locale_files]
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
