import sys
import os

prompt = sys.argv[1]

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Build the path to the log file relative to the script location
log_path = os.path.join(script_dir, '../user-prompts-log.md')
with open(log_path, 'a', encoding='utf-8') as f:
    f.write('\n---\n')
    f.write(f'{prompt}\n')

