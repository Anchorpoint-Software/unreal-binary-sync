import anchorpoint as ap
import apsync as aps
import os
import subprocess
import zipfile
import psutil
import glob

ctx = ap.get_context()
ui = ap.UI()

def unzip_and_manage_files(zip_file_path, project_path, progress):
    # Delete existing files from previous sync if extracted_binaries.txt exists
    binary_list_path = os.path.join(project_path, "extracted_binaries.txt")
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
    
    # Create a new progress object for extraction
    progress.finish()
    extraction_progress = ap.Progress("Extracting Binaries", "Preparing to extract files...", infinite=False)
    extraction_progress.set_cancelable(True)
    
    # Unzip the file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # Get the total number of files to unzip
        total_files = len(zip_ref.infolist())
        extraction_progress.set_text("Extracting files...")
        
        # Extract all files, overwriting existing ones
        for index, file_info in enumerate(zip_ref.infolist()):
            # Stop process if cancel was hit by user
            if extraction_progress.canceled:
                ui.show_info("Process cancelled")
                extraction_progress.finish()
                return False
            
            zip_ref.extract(file_info, project_path)
            unzipped_files.append(file_info.filename)
            extraction_progress.report_progress((index + 1) / total_files)  # Report the progress
    
    # Write the list of unzipped files to extracted_binaries.txt
    with open(binary_list_path, 'w') as f:
        f.write(f"Binary sync from {os.path.basename(zip_file_path)}\n")
        f.write("=" * 50 + "\n")
        for file in sorted(unzipped_files):
            f.write(f"{file}\n")
    
    extraction_progress.finish()
    return True  # Indicate success

def run_setup(project_path, progress):
    import ctypes
    import sys
    
    # Check if running with admin rights, if not, try to elevate
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    # Finish the incoming progress object
    progress.finish()
    
    # Create a new progress object for dependencies
    setup_progress = ap.Progress("Setting up project", "Setting up project dependencies...", infinite=True)
    setup_progress.set_cancelable(True)
    
    # Create a null device to redirect unwanted output for some processes
    devnull = open(os.devnull, 'w')
    
    try:
        # Step 1: Run GitDependencies.exe
        git_dependencies_path = os.path.join(project_path, "Engine", "Binaries", "DotNET", "GitDependencies", "win-x64", "GitDependencies.exe")
        if os.path.exists(git_dependencies_path):
            # Create a new progress for dependencies syncing
            setup_progress.finish()
            dep_progress = ap.Progress("Setting up Project", "Checking dependencies...", infinite=True)
            dep_progress.set_cancelable(True)
            
            # Prepare startupinfo to hide the window
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Run with --force parameter to avoid prompts
            process = subprocess.Popen(
                [git_dependencies_path, "--force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_path,
                startupinfo=startupinfo
            )
            
            # Read and print output while checking for cancellation
            while process.poll() is None:
                # Check for cancellation
                if dep_progress.canceled:
                    process.terminate()
                    ui.show_info("Setup cancelled by user")
                    dep_progress.finish()
                    return False
                
                # Read output
                output_line = process.stdout.readline()
                if output_line:
                    
                    # Parse progress percentage if present
                    if "Updating dependencies:" in output_line:
                        try:
                            # Extract percentage from strings like "Updating dependencies: 3% (3476/90939)"
                            percent_str = output_line.split("%")[0].split(": ")[1].strip()
                            percent = float(percent_str) / 100.0  # Convert to 0-1 range
                            dep_progress.set_text(output_line)
                            dep_progress.report_progress(percent)
                        except (IndexError, ValueError) as e:
                            # If parsing fails, just continue
                            pass
            
            # Get final return code
            if process.returncode != 0:
                ui.show_error("GitDependencies Error", "Failed to sync dependencies")
                dep_progress.finish()
                return False
            
            # Finish the dependencies progress
            dep_progress.finish()
            
            # Create a new progress object for the rest of the steps
            hooks_progress = ap.Progress("Finishing setup", "Registering git hooks...", infinite=True)
            hooks_progress.set_cancelable(True)
            
        # Step 2: Setup git hooks
        git_hooks_path = os.path.join(project_path, ".git", "hooks")
        if os.path.exists(git_hooks_path):
            hooks_progress.set_text("Registering git hooks...")
            
            # Create post-checkout hook
            with open(os.path.join(git_hooks_path, "post-checkout"), 'w') as f:
                f.write("#!/bin/sh\n")
                f.write("Engine/Binaries/DotNET/GitDependencies/win-x64/GitDependencies.exe\n")
            
            # Create post-merge hook
            with open(os.path.join(git_hooks_path, "post-merge"), 'w') as f:
                f.write("#!/bin/sh\n")
                f.write("Engine/Binaries/DotNET/GitDependencies/win-x64/GitDependencies.exe\n")
            
            print("Git hooks registered successfully")
            
        # Check for cancellation
        if hooks_progress.canceled:
            ui.show_info("Setup cancelled by user")
            hooks_progress.finish()
            return False
            
        # Step 3: Install prerequisites
        prereq_path = os.path.join(project_path, "Engine", "Extras", "Redist", "en-us", "UEPrereqSetup_x64.exe")
        if os.path.exists(prereq_path):
            hooks_progress.set_text("Installing prerequisites. Make sure to accept the UAC prompt...")
            
            # Prepare special startupinfo to suppress UAC dialog as much as possible
            uac_startupinfo = None
            if os.name == 'nt':
                uac_startupinfo = subprocess.STARTUPINFO()
                uac_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                # Use SW_HIDE to hide the window
                uac_startupinfo.wShowWindow = 0  # SW_HIDE
            
            # Run the prerequisites installer with maximum silent flags
            try:
                # Try to run with administrator privileges without showing UAC prompt
                process = subprocess.Popen(
                    [prereq_path, "/quiet", "/norestart", "/SILENT", "/SUPPRESSMSGBOXES"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=project_path,
                    startupinfo=uac_startupinfo
                )
                
                # Wait for completion with cancellation support
                while process.poll() is None:
                    if hooks_progress.canceled:
                        process.terminate()
                        ui.show_info("Setup cancelled by user")
                        hooks_progress.finish()
                        return False
                
                print("Prerequisites installed successfully")
            
            except Exception as e:
                print(f"Warning: Prerequisites installation encountered an issue: {str(e)}")
                print("Continuing with next steps...")
                # Continue anyway as this may not be critical
            
        # Check for cancellation
        if hooks_progress.canceled:
            ui.show_info("Setup cancelled by user")
            hooks_progress.finish()
            return False
            
        # Step 4: Register engine installation
        version_selector_path = os.path.join(project_path, "Engine", "Binaries", "Win64", "UnrealVersionSelector-Win64-Shipping.exe")
        if os.path.exists(version_selector_path):
            hooks_progress.set_text("Registering engine installation...")
            
            # Register the engine
            process = subprocess.Popen(
                [version_selector_path, "/register", "/unattended"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_path,
                startupinfo=startupinfo
            )
            
            # Wait for completion with cancellation support
            while process.poll() is None:
                if hooks_progress.canceled:
                    process.terminate()
                    ui.show_info("Setup cancelled by user")
                    hooks_progress.finish()
                    return False
            
            print("Engine registered successfully")
            
        hooks_progress.set_text("Setup completed successfully")
        hooks_progress.finish()
        return True
        
    except Exception as e:
        ui.show_error("Setup Error", str(e))
        return False

def is_unreal_running(project_path):
    unreal_exe = os.path.join(project_path, "Engine", "Binaries", "Win64", "UnrealEditor.exe")
    
    # Get the absolute path to handle any case differences
    unreal_exe = os.path.abspath(unreal_exe)
    
    # Check all running processes
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            # Get process info
            proc_info = proc.info
            if proc_info['exe']:
                # Compare the absolute paths
                if os.path.abspath(proc_info['exe']) == unreal_exe:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def find_uproject_files(project_path):
    uproject_files = []
    depth = 3
    
    # Get all directories at the specified depth (currently set to depth levels)
    for root, dirs, files in os.walk(project_path, topdown=True):
        # Skip Engine and Templates folders
        if 'Engine' in dirs:
            dirs.remove('Engine')
        if 'Templates' in dirs:
            dirs.remove('Templates')
            
        # Only process up to depth levels deep
        rel_path = os.path.relpath(root, project_path)
        if rel_path == '.' or rel_path.count(os.sep) <= depth:
            # Look for .uproject files in current directory
            for file in files:
                if file.endswith('.uproject'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, project_path)
                    uproject_files.append(rel_path)
        
        # Stop walking deeper than depth levels
        if rel_path.count(os.sep) >= depth:
            dirs.clear()
    
    return uproject_files

def sync_action(dialog,launch_project_path):
    # Set the sync button to processing state
    dialog.set_processing("sync_button", True, "Initializing...")
    
    source_path = dialog.get_value("binary_source")
    sync_dependencies = dialog.get_value("sync_dependencies")
    launch_project_display_name = dialog.get_value("launch_project_display_name")
    
    # Store the settings for next time
    settings = aps.Settings()
    settings.set("last_binary_source", source_path)
    settings.set("sync_dependencies", sync_dependencies)
    settings.set("launch_project_display_name", launch_project_display_name)
    settings.store()

    # Get project path before closing dialog
    project_path = ctx.project_path
    
    # Check if Unreal Editor is running
    if is_unreal_running(project_path):
        dialog.set_processing("sync_button", False)
        ui.show_info("Unreal Editor is running", "Please close Unreal Engine before proceeding with the binary sync.")
        return

    progress = ap.Progress("Syncing Binaries", infinite=True)
    progress.set_cancelable(True)
    
    dialog.close()
    
    # Get commit IDs from the Git repository
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
        return
    
    # Limit the number of commits to check
    max_depth = 50
    commit_ids = commit_ids[:max_depth]

    # Iterate through commit IDs and check for matching zip files
    for commit_id in commit_ids:
        zip_file_name = f"{commit_id}.zip"
        zip_file_path = os.path.join(source_path, zip_file_name)
        if zip_file_name in os.listdir(source_path):
            
            # Run the setup script if enabled
            if sync_dependencies:
                if not run_setup(project_path, progress):
                    return
            
            try:
                if not unzip_and_manage_files(zip_file_path, project_path, progress):
                    return  # If extraction was canceled or failed
                
                # Launch the selected uproject file if one was selected
                if launch_project_path:
                    # Check if the path is relative (doesn't have a drive letter on Windows or doesn't start with / on Unix)
                    if not os.path.isabs(launch_project_path):
                        # Append the relative path to the project_path to get the absolute path
                        launch_project_path = os.path.join(project_path, launch_project_path)
                    
                    if os.path.exists(launch_project_path):
                        try:
                            subprocess.Popen([launch_project_path], shell=True)
                            ui.show_success("Binaries synced", f"Launching project {os.path.basename(launch_project_path)}")
                        except Exception as e:
                            ui.show_info("Binaries synced", f"Failed to launch project: {str(e)}")
                else:
                    ui.show_success("Binaries synced", f"Files extracted from {zip_file_name}")
                return
                
            except Exception as e:
                ui.show_error("Extraction failed", str(e))
                return
    
    # If no matching zip file is found
    ui.show_error("No compatible binaries found", "Check your binaries source folder")

def show_dialog():

    uproject_files = find_uproject_files(ctx.project_path)
    uproject_display_names = [os.path.splitext(os.path.basename(uproject_file))[0] for uproject_file in uproject_files]
    uproject_display_names.append("No Project")
    if not uproject_files:
        ui.show_error("Not an Unreal project", "Check your project folder")
        return

    settings = aps.Settings()
    last_binary_source = settings.get("last_binary_source", "")
    sync_dependencies = settings.get("sync_dependencies", True)
    launch_project_display_name = settings.get("launch_project_display_name", uproject_files[0])       
    
    def run_sync_action_async(dialog):
        launch_project_path = "" 
        for uproject_file in uproject_files:
            if dialog.get_value("launch_project_display_name") in uproject_file:
                launch_project_path = uproject_file
                break
        ctx.run_async(sync_action,dialog,launch_project_path)

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
        text="Sync Setup Dependencies",
        var="sync_dependencies",
        default=sync_dependencies
    )
    dialog.add_info("Note that you have to accept a Windows Control Popup for UE Prerequisites")    
    
    if launch_project_display_name != "":
        dialog.add_text("Launch Project").add_dropdown(
            default=launch_project_display_name,
            values=uproject_display_names,
            var="launch_project_display_name"
        )    
    
    dialog.add_button("Sync", callback=run_sync_action_async, var="sync_button")
    dialog.show()

if __name__ == "__main__":
    show_dialog()