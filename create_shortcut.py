"""Create a desktop shortcut for SyncPlay."""
import os
import sys
from pathlib import Path

def create_desktop_shortcut():
    """Create a .lnk shortcut on the Windows desktop."""
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Installing required packages...")
        os.system(f"{sys.executable} -m pip install pywin32 winshell")
        import winshell
        from win32com.client import Dispatch
    
    # Paths
    desktop = winshell.desktop()
    project_root = Path(__file__).parent.resolve()
    launcher = project_root / "launch_syncplay.pyw"
    icon = project_root / "music_player" / "resources" / "icon.ico"
    
    # Create shortcut
    shortcut_path = Path(desktop) / "SyncPlay.lnk"
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = sys.executable.replace("python.exe", "pythonw.exe")
    shortcut.Arguments = f'"{launcher}"'
    shortcut.WorkingDirectory = str(project_root)
    shortcut.IconLocation = str(icon)
    shortcut.Description = "SyncPlay - Music Player with Lyric Overlay"
    shortcut.save()
    
    print(f"✓ Desktop shortcut created: {shortcut_path}")

if __name__ == "__main__":
    create_desktop_shortcut()
