import anchorpoint as ap
import apsync as aps
import os
import subprocess
import zipfile

ctx = ap.get_context()
ui = ap.UI()

def sync_action(dialog):
    source_path = dialog.get_value("binary_source")
    include_editor_binaries = dialog.get_value("include_editor_binaries")
    progress = ap.Progress("Syncing Binaries", infinite=True)
    progress.set_cancelable(True)
    
    # Store the selected path in settings
    settings = aps.Settings()
    settings.set("last_binary_source", source_path)
    settings.store()
    
    # Get commit IDs from the Git repository
    project_path = ctx.project_path  # Assuming ctx.project_path is the correct attribute
    try:
        startupinfo = None
        if os.name == 'nt':  # Check if the OS is Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        commit_ids = subprocess.check_output(
            ['git', 'rev-list', 'HEAD'],
            cwd=project_path,
            text=True,
            startupinfo=startupinfo
        ).splitlines()
    except subprocess.CalledProcessError:
        ui.show_error("Git Error", "Failed to retrieve commit IDs.")
        dialog.close()
        return
    
    # Limit the number of commits to check
    max_depth = 50
    commit_ids = commit_ids[:max_depth]

    # Iterate through commit IDs and check for matching zip files
    for commit_id in commit_ids:
        zip_file_name = f"{commit_id}.zip"
        zip_file_path = os.path.join(source_path, zip_file_name)
        if zip_file_name in os.listdir(source_path):
            try:
                # Delete existing files from previous sync if binary_list.txt exists
                binary_list_path = os.path.join(project_path, "binary_list.txt")
                if os.path.exists(binary_list_path):
                    with open(binary_list_path, 'r') as file:
                        # Skip the header lines
                        next(file)  # Skip "Binary sync from..." line
                        next(file)  # Skip separator line
                        for line in file:
                            file_path = line.strip()
                            full_path = os.path.join(project_path, file_path)
                            if os.path.exists(full_path):
                                os.remove(full_path)

                # Create a list to store unzipped files
                unzipped_files = []
                
                # Unzip the file
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    # Get the total number of files to unzip
                    total_files = len(zip_ref.infolist())
                    progress.set_text("Extracting files...")
                    
                    # Extract all files, overwriting existing ones
                    for index, file_info in enumerate(zip_ref.infolist()):
                        # Stop process if cancel was hit by user
                        if progress.canceled:
                            print("Unzipping process was canceled.")
                            progress.finish()
                            return False
                        
                        zip_ref.extract(file_info, project_path)
                        unzipped_files.append(file_info.filename)
                        progress.report_progress((index + 1) / total_files)  # Report the progress
                
                # Write the list of unzipped files to binary_list.txt
                binary_list_path = os.path.join(project_path, "binary_list.txt")
                with open(binary_list_path, 'w') as f:
                    f.write(f"Binary sync from {zip_file_name}\n")
                    f.write("=" * 50 + "\n")
                    for file in sorted(unzipped_files):
                        f.write(f"{file}\n")
                
                ui.show_success("Binaries synced", f"Files extracted from {zip_file_name}")
                progress.finish()
                dialog.close()
                return
                
            except Exception as e:
                ui.show_error("Extraction failed", str(e))
                dialog.close()
                return
    
    # If no matching zip file is found
    ui.show_error("No compatible binaries found", "Check your binaries source folder")
    dialog.close()

def show_dialog():

    def run_sync_action_async(dialog):
        ctx.run_async(sync_action,dialog)

    settings = aps.Settings()
    last_binary_source = settings.get("last_binary_source", "")

    dialog = ap.Dialog()
    dialog.title = "Sync Binaries"
    
    if ctx.icon:
        dialog.icon = ctx.icon
    
    dialog.add_text("Binary source").add_input(
        placeholder="Select folder containing binaries...",
        browse=ap.BrowseType.Folder,
        var="binary_source",
        default=last_binary_source
    )
    
    dialog.add_checkbox(
        text="Include Editor Binaries",
        var="include_editor_binaries"
    )
    
    dialog.add_button("Sync", callback=run_sync_action_async)
    dialog.show()

if __name__ == "__main__":
    show_dialog()