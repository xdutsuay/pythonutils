import os
import subprocess
import sys

# Replace 'file_path' with the path of the file containing the imports
file_path = 'path/to/file.py'

# Parse the file to get a list of required packages
with open(file_path) as f:
    required_packages = []
    for line in f:
        if line.startswith('import') or line.startswith('from'):
            package_name = line.split()[1]
            if '.' in package_name:
                package_name = package_name.split('.')[0]
            required_packages.append(package_name)

# Create a virtual environment and activate it
venv_name = 'venv'
subprocess.run(['python', '-m', 'venv', venv_name])
if sys.platform == 'win32':
    activate_script = os.path.join(venv_name, 'Scripts', 'activate.bat')
else:
    activate_script = os.path.join(venv_name, 'bin', 'activate')
subprocess.run(['source', activate_script], shell=True)

# Install required packages using pip
for package in required_packages:
    subprocess.run(['pip', 'install', package])
