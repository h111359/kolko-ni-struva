#!/usr/bin/env python3
"""
This script compiles the contents of specific files into a single markdown file for context clarification.
It is intended to be run in the root of an AIB workspace, where the .aib_brain and .aib_memory directories are located.
The output file will be named context-compilation-<timestamp>.md and will be placed in the .aib_memory directory.
Usage:
    python .aib_brain/tools/create-clarify-context.py
"""
import os
import datetime

def main():
    # Define the files to include in the compilation
    files_to_include = [
        os.path.join(".aib_brain", "prompts", "aib-clarify.md"),    
        os.path.join(".aib_memory", "context.md"),
        os.path.join(".aib_brain", "conventions", "context-convention.md"),
        os.path.join(".aib_brain", "conventions", "q-block-convention.md"),
        os.path.join(".aib_brain", "conventions", "requirements-analysis-convention.md")
    ]

    # Generate timestamp and output file path
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_filename = f"context-compilation-{timestamp}.md"
    output_path = os.path.join(".aib_memory", output_filename)

    # Ensure .aib_memory directory exists (though it always should in an AIB workspace)
    os.makedirs(".aib_memory", exist_ok=True)

    try:
        with open(output_path, 'w', encoding='utf-8') as out_file:
            for file_path in files_to_include:
                file_name = os.path.basename(file_path)
                out_file.write(f"# {file_name}\n\n")
                
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as in_file:
                        out_file.write(in_file.read())
                else:
                    out_file.write(f"*(File {file_path} not found in the workspace)*\n")
                
                out_file.write("\n\n---\n\n")
                
        print(f"Context compilation created successfully: {output_path}")
    except Exception as e:
        print(f"Error creating context compilation: {e}")
        exit(1)

if __name__ == "__main__":
    main()