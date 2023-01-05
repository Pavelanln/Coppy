import os
import subprocess
import sys


if 'BUILD_ENVIRONMENT' not in os.environ:
    os.environ['CONDA_PARENT_DIR'] = str(os.getcwd())
else:
    os.environ['CONDA_PARENT_DIR'] = 'C:\\Jenkins'


# Be conservative here when rolling out the new AMI with conda. This will try
# to install conda as before if it couldn't find the conda installation. This
# can be removed eventually after we gain enough confidence in the AMI

os.environ['INSTALL_FRESH_CONDA'] = '1'
install_fresh_conda = '1'


if not 'CONDA_ENV_RUN' in os.environ:
    os.environ['INSTALL_FRESH_CONDA'] = '1'
    install_fresh_conda = '1'

elif 'INSTALL_FRESH_CONDA' in os.environ:
    install_fresh_conda = os.environ['INSTALL_FRESH_CONDA']




conda_parent_dir = os.environ['CONDA_PARENT_DIR']
tmp_dir_win = os.environ['TMP_DIR_WIN']


if install_fresh_conda == '1':

    try:
        subprocess.run(['echo', 'Installing conda to: ' + conda_parent_dir + '\\Miniconda3'])

        subprocess.run(['curl', '--retry', '3', '-k',
            'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe',
                '--output', tmp_dir_win + '\\Miniconda3-latest-Windows-x86_64.exe'])

        subprocess.run([tmp_dir_win + '\\Miniconda3-latest-Windows-x86_64.exe',
            '/InstallationType=JustMe', '/RegisterPython=0', '/S', '/AddToPath=1',
                '/D=' + conda_parent_dir + '\\Miniconda3'])

        subprocess.run(['echo', 'Installed conda to: ' + conda_parent_dir + '\\Miniconda3'])

        os.environ['PATH'] = conda_parent_dir + '\\Miniconda3\\Library\\bin;' + conda_parent_dir +\
            '\\Miniconda3;' + conda_parent_dir + '\\Miniconda3\\Scripts;' + os.environ['PATH']

    except Exception as e:

        subprocess.run(['echo', 'activate conda failed'])
        subprocess.run(['echo', e])
        sys.exit()


# Activate conda so that we can use its commands, i.e. conda, python, pip
subprocess.run(['conda', 'create', '--prefix', conda_parent_dir + '\\Miniconda3\\\envs\\test_env'], shell=True)


if install_fresh_conda == '1':

    try:

        subprocess.run(['conda', 'install', '-n', 'test_env', '-y', '-q', 'numpy', 'cffi', 'pyyaml', 'boto3', 'libuv'])

        subprocess.run(['conda', 'install', '-n', 'test_env', '-y', '-q', '-c', 'conda-forge', 'cmake=3.22.3'])

    except Exception as e:

        subprocess.run(['echo', 'activate conda failed'])
        subprocess.run(['echo', e])
        sys.exit()
