"""
Cross-platform library loader for STDF parser C++ extension
"""
import os
import sys
import platform

def setup_library_path():
    """Setup library paths for cross-platform compatibility"""
    
    # Get the directory containing this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    lib_dir = os.path.join(project_root, "cpp", "third_party", "lib")
    
    system = platform.system().lower()
    
    if system == "linux" or system == "darwin":  # Linux/macOS
        # Set LD_LIBRARY_PATH (Linux) or DYLD_LIBRARY_PATH (macOS)
        env_var = "LD_LIBRARY_PATH" if system == "linux" else "DYLD_LIBRARY_PATH"
        current_path = os.environ.get(env_var, "")
        if lib_dir not in current_path:
            os.environ[env_var] = f"{lib_dir}:{current_path}" if current_path else lib_dir
            
    elif system == "windows":
        # Windows: Multiple approaches for DLL loading
        dll_loaded = False
        
        # Method 1: Python 3.8+ add_dll_directory (recommended)
        if hasattr(os, 'add_dll_directory') and sys.version_info >= (3, 8):
            try:
                os.add_dll_directory(lib_dir)
                dll_loaded = True
                print(f"✅ Added DLL directory: {lib_dir}")
            except (OSError, FileNotFoundError) as e:
                print(f"⚠️  add_dll_directory failed: {e}")
        
        # Method 2: Copy DLLs to current directory (most reliable)
        if not dll_loaded:
            try:
                import glob
                import shutil
                dll_files = glob.glob(os.path.join(lib_dir, "*.dll"))
                current_dir = os.getcwd()
                
                for dll in dll_files:
                    dll_name = os.path.basename(dll)
                    target = os.path.join(current_dir, dll_name)
                    if not os.path.exists(target):
                        shutil.copy2(dll, target)
                        print(f"📦 Copied DLL: {dll_name}")
                        dll_loaded = True
            except Exception as e:
                print(f"⚠️  DLL copy failed: {e}")
        
        # Method 3: Fallback to PATH (least reliable but widely compatible)
        if not dll_loaded:
            current_path = os.environ.get("PATH", "")
            if lib_dir not in current_path:
                os.environ["PATH"] = f"{lib_dir};{current_path}"
                print(f"📂 Added to PATH: {lib_dir}")
    
    return lib_dir

# Auto-setup when imported
setup_library_path()