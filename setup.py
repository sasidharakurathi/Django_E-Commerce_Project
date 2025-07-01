#!/usr/bin/env python3

#Note: setup.py is still in development. Issues may occur.
"""
Setup script for Django E-Commerce Platform with Face Recognition
Author: Akurathi Sasidhar
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def create_virtual_environment():
    """Create virtual environment"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("📁 Virtual environment already exists")
        return True
    
    return run_command("python -m venv venv", "Creating virtual environment")

def activate_virtual_environment():
    """Get activation command for virtual environment"""
    if os.name == 'nt':  # Windows
        return "venv\\Scripts\\activate"
    else:  # macOS/Linux
        return "source venv/bin/activate"

def install_dependencies():
    """Install Python dependencies"""
    pip_command = "venv\\Scripts\\pip" if os.name == 'nt' else "venv/bin/pip"
    return run_command(f"{pip_command} install -r requirement.txt", "Installing dependencies")

def setup_environment_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("📄 .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file with your configuration!")
        return True
    else:
        print("❌ .env.example file not found")
        return False

def setup_database():
    """Setup Django database"""
    python_command = "venv\\Scripts\\python" if os.name == 'nt' else "venv/bin/python"
    
    commands = [
        (f"{python_command} manage.py makemigrations", "Creating database migrations"),
        (f"{python_command} manage.py migrate", "Applying database migrations"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def create_superuser():
    """Create Django superuser"""
    python_command = "venv\\Scripts\\python" if os.name == 'nt' else "venv/bin/python"
    print("\n👤 Creating superuser account...")
    print("Please follow the prompts to create an admin account:")
    
    try:
        subprocess.run(f"{python_command} manage.py createsuperuser", shell=True, check=True)
        print("✅ Superuser created successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create superuser")
        return False

def setup_face_recognition():
    """Setup face recognition directories"""
    print("\n🎭 Setting up face recognition...")
    
    directories = [
        "ecom/FaceRecognition/dataset",
        "ecom/FaceRecognition/encodings"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    print("✅ Face recognition setup completed!")
    return True

def print_next_steps():
    """Print next steps for the user"""
    activation_cmd = activate_virtual_environment()
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\n📋 Next Steps:")
    print(f"1. Activate virtual environment: {activation_cmd}")
    print("2. Edit .env file with your configuration")
    print("3. Run the development server: python manage.py runserver")
    print("4. Access the application at: http://127.0.0.1:8000/")
    print("5. Access admin panel at: http://127.0.0.1:8000/admin/")
    print("\n📖 For detailed instructions, see README.md")
    print("\n🎭 Face Recognition Setup:")
    print("- Add face images to ecom/FaceRecognition/dataset/username/")
    print("- Run: python ecom/FaceRecognition/encode_faces.py")
    print("\n⚠️  Important:")
    print("- Configure email settings in .env for contact form")
    print("- Set up PayPal credentials for payments")
    print("- Review security settings before deployment")

def main():
    """Main setup function"""
    print("🚀 Django E-Commerce Platform Setup")
    print("Author: Akurathi Sasidhar")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment file
    if not setup_environment_file():
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    # Setup face recognition
    if not setup_face_recognition():
        sys.exit(1)
    
    # Create superuser
    create_superuser()  # Optional, don't exit on failure
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()
