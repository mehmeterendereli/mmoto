#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform

def is_windows():
    """
    Check if the current system is Windows
    
    Returns:
        bool: True if the system is Windows, False otherwise
    """
    return platform.system().lower() == "windows"

def run_command(command, shell=True, check=True, capture_output=False):
    """
    Run a command in a cross-platform way
    
    Args:
        command (str): Command to run
        shell (bool): Whether to use shell
        check (bool): Whether to check the return code
        capture_output (bool): Whether to capture the output
        
    Returns:
        subprocess.CompletedProcess: Result of the command
    """
    try:
        if is_windows():
            # Windows PowerShell doesn't support && for command chaining
            # Replace it with ;
            if "&&" in command:
                command = command.replace("&&", ";")
                
        return subprocess.run(
            command, 
            shell=shell, 
            check=check, 
            capture_output=capture_output, 
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        raise
    except Exception as e:
        print(f"Error running command: {e}")
        raise

def run_multiple_commands(commands, shell=True, check=True, capture_output=False):
    """
    Run multiple commands in sequence
    
    Args:
        commands (list): List of commands to run
        shell (bool): Whether to use shell
        check (bool): Whether to check the return code
        capture_output (bool): Whether to capture the output
        
    Returns:
        list: List of results for each command
    """
    results = []
    
    for cmd in commands:
        try:
            result = run_command(cmd, shell, check, capture_output)
            results.append(result)
        except Exception as e:
            print(f"Command failed: {cmd}")
            print(f"Error: {e}")
            if check:
                raise
            
    return results

def get_shell_delimiter():
    """
    Get the correct command delimiter for the current shell
    
    Returns:
        str: The command delimiter
    """
    if is_windows():
        return ";"
    else:
        return "&&" 