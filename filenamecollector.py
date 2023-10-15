import os

def list_files_in_folder(folder_path):
    try:
        # Initialize an empty list to store file names
        file_names = []

        # Recursive function to traverse through all subfolders
        def traverse_folder(current_folder):
            for item in os.listdir(current_folder):
                item_path = os.path.join(current_folder, item)
                if os.path.isfile(item_path):
                    # If it's a file, add it to the list
                    file_names.append(item)
                elif os.path.isdir(item_path):
                    # If it's a directory, recursively traverse it
                    traverse_folder(item_path)

        # Start the traversal from the specified folder
        traverse_folder(folder_path)

        # Write the file names to file_names.txt
        with open('file_names.txt', 'w') as file:
            for file_name in file_names:
                file.write(file_name + '\n')

        print(f"File names written to file_names.txt")

    except Exception as e:
        print(f"Error: {e}")

# Specify the folder path here (replace 'C:/Your/Folder/Path' with the actual path)
folder_path = r'C:/Your/Folder/Path'

# Call the function with the specified folder path
list_files_in_folder(folder_path)
