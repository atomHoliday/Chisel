project(
    'chisel',
    'c',
    version: '0.1.0',
    meson_version: '>= 0.60.0',
)

python = import('python')
python_installation = python.find_installation('python3')

install_subdir(
    'document',
    install_dir: python_installation.get_install_dir() / 'chisel',
)
install_subdir(
    'tools',
    install_dir: python_installation.get_install_dir() / 'chisel',
)
install_subdir(
    'drawing',
    install_dir: python_installation.get_install_dir() / 'chisel',
)
install_subdir(
    'ui',
    install_dir: python_installation.get_install_dir() / 'chisel',
)
install_subdir(
    'debug',
    install_dir: python_installation.get_install_dir() / 'chisel',
)

python_installation.install_source('main.py')
python_installation.install_source('canvas.py')
python_installation.install_source('window.py')

desktop_file = 'com.uncapyeti.chisel.desktop'
i18n = import('i18n')

install_data(
    desktop_file,
    install_dir: get_option('datadir') / 'applications',
)

install_data(
    'com.uncapyeti.chisel.svg',
    install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data(
    'com.uncapyeti.chisel-symbolic.svg',
    install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'symbolic' / 'apps',
)
