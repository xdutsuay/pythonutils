import subprocess

# Use subprocess to run bcdedit commands
def run_bcdedit_command(args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output, error

# Get current boot configuration
def get_current_boot_configuration():
    output, error = run_bcdedit_command(['bcdedit', '/enum'])
    return output.decode('utf-8'), error.decode('utf-8')

# Modify boot configuration
def set_boot_configuration(identifier, setting, value):
    run_bcdedit_command(['bcdedit', '/set', identifier, setting, value])

# Example usage
if __name__ == '__main__':
    # Get current boot configuration
    config, error = get_current_boot_configuration()
    print(config)
    
    # Modify boot configuration (set timeout to 5 seconds)
    set_boot_configuration('{current}', 'timeout', '5')
