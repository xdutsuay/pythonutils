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

# Check if Secure Boot is currently enabled
def is_secure_boot_enabled():
    output, error = run_bcdedit_command(['bcdedit', '/enum', '{current}'])
    output_str = output.decode('utf-8')
    return 'SecureBoot' in output_str and 'Yes' in output_str

# Enable or disable Secure Boot
def set_secure_boot_enabled(enabled):
    identifier = '{current}'
    if enabled:
        set_boot_configuration(identifier, 'integrityservices', 'Enabled')
        set_boot_configuration(identifier, 'SecureBoot', 'On')
    else:
        set_boot_configuration(identifier, 'SecureBoot', 'Off')
        set_boot_configuration(identifier, 'integrityservices', 'Ignored')

# Example usage
if __name__ == '__main__':
    # Get current boot configuration
    config, error = get_current_boot_configuration()
    print(config)

    # Check if Secure Boot is currently enabled
    secure_boot_enabled = is_secure_boot_enabled()
    print('Secure Boot is currently', 'enabled' if secure_boot_enabled else 'disabled')

    # Enable or disable Secure Boot
    new_secure_boot_enabled = input('Do you want to enable Secure Boot? (y/n): ')
    if new_secure_boot_enabled.lower() == 'y':
        set_secure_boot_enabled(True)
        print('Secure Boot has been enabled.')
    else:
        set_secure_boot_enabled(False)
        print('Secure Boot has been disabled.')
