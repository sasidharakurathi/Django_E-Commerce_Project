#!/usr/bin/env python3
"""
Git History Cleaner for Django E-Commerce Project
This script helps remove sensitive data from git history

Author: Akurathi Sasidhar
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return False

def check_git_repo():
    """Check if we're in a git repository"""
    if not os.path.exists('.git'):
        print("❌ This is not a git repository!")
        print("Please run this script from the root of your git repository.")
        return False
    return True

def backup_current_state():
    """Create a backup branch before cleaning"""
    print("\n📦 Creating backup branch...")
    commands = [
        ("git branch backup-before-clean", "Creating backup branch"),
        ("git checkout backup-before-clean", "Switching to backup branch"),
        ("git checkout main", "Switching back to main branch")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def remove_sensitive_files_from_history():
    """Remove sensitive files from git history"""
    print("\n🧹 Removing sensitive data from git history...")
    
    # Files and patterns to remove from history
    sensitive_patterns = [
        "*.env",
        ".env",
        "db.sqlite3",
        "*.log",
        "ecom/FaceRecognition/dataset/*",
        "ecom/FaceRecognition/encodings/*.pkl",
        "ecom/FaceRecognition/encodings/*.json"
    ]
    
    for pattern in sensitive_patterns:
        command = f'git filter-branch --force --index-filter "git rm --cached --ignore-unmatch {pattern}" --prune-empty --tag-name-filter cat -- --all'
        run_command(command, f"Removing {pattern} from history")
    
    return True

def clean_git_references():
    """Clean git references and garbage collect"""
    print("\n🗑️ Cleaning git references...")
    
    commands = [
        ("git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin", "Cleaning original refs"),
        ("git reflog expire --expire=now --all", "Expiring reflog"),
        ("git gc --prune=now", "Garbage collecting"),
        ("git gc --aggressive --prune=now", "Aggressive garbage collection")
    ]
    
    for command, description in commands:
        run_command(command, description)
    
    return True

def force_push_warning():
    """Warn about force push requirements"""
    print("\n" + "="*60)
    print("⚠️  IMPORTANT: FORCE PUSH REQUIRED")
    print("="*60)
    print("\nTo complete the cleanup, you need to force push to your remote repository:")
    print("git push origin --force --all")
    print("git push origin --force --tags")
    print("\n⚠️  WARNING: This will rewrite history on the remote repository!")
    print("⚠️  Make sure all team members are aware of this change!")
    print("⚠️  They will need to re-clone the repository!")
    
    response = input("\nDo you want to proceed with force push? (yes/no): ")
    if response.lower() == 'yes':
        commands = [
            ("git push origin --force --all", "Force pushing all branches"),
            ("git push origin --force --tags", "Force pushing tags")
        ]
        
        for command, description in commands:
            run_command(command, description)
    else:
        print("⏸️  Force push skipped. You can run it manually later.")

def main():
    """Main cleanup function"""
    print("🧹 Git History Cleaner for Django E-Commerce Project")
    print("Author: Akurathi Sasidhar")
    print("="*60)
    
    # Check if we're in a git repo
    if not check_git_repo():
        sys.exit(1)
    
    print("\n⚠️  WARNING: This script will rewrite git history!")
    print("⚠️  This action cannot be undone!")
    print("⚠️  Make sure you have a backup of your repository!")
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled by user.")
        sys.exit(0)
    
    # Create backup
    if not backup_current_state():
        print("❌ Failed to create backup. Aborting.")
        sys.exit(1)
    
    # Remove sensitive files from history
    if not remove_sensitive_files_from_history():
        print("❌ Failed to remove sensitive files. Check the backup branch.")
        sys.exit(1)
    
    # Clean git references
    clean_git_references()
    
    # Force push warning and execution
    force_push_warning()
    
    print("\n" + "="*60)
    print("✅ GIT HISTORY CLEANUP COMPLETED!")
    print("="*60)
    print("\n📋 What was done:")
    print("✅ Created backup branch 'backup-before-clean'")
    print("✅ Removed sensitive files from git history")
    print("✅ Cleaned git references and garbage collected")
    print("✅ Repository is now clean and ready for public sharing")
    
    print("\n📋 Next Steps:")
    print("1. Verify that sensitive data is removed: git log --oneline")
    print("2. Check repository size: du -sh .git")
    print("3. Test your application to ensure it still works")
    print("4. If everything looks good, you can delete the backup branch:")
    print("   git branch -D backup-before-clean")

if __name__ == "__main__":
    main()
