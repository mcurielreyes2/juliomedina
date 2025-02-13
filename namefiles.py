import os
import csv


def list_files_to_csv(folder_path, output_csv_path):
    """
    Lists all files in the specified folder and writes the filenames to a CSV.

    Parameters:
    -----------
    folder_path : str
        The path to the folder whose filenames you want to list.
    output_csv_path : str
        The path (including filename) of the CSV file where results will be saved.
    """
    # Get the list of all items in the folder (files + subfolders).
    items = os.listdir(folder_path)

    # Filter out directories (if you only want files).
    # Comment out this line if you want to include folder names too.
    files = [item for item in items if os.path.isfile(os.path.join(folder_path, item))]

    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Write a header row (optional)
        writer.writerow(["Filename"])

        # Write each file's name to a new row
        for filename in files:
            writer.writerow([filename])

    print(f"Successfully saved {len(files)} filenames to {output_csv_path}")


if __name__ == "__main__":
    # Example usage:
    folder_path = r"./static/docs"
    output_csv_path = r"files_list.csv"

    list_files_to_csv(folder_path, output_csv_path)