import os
import sys
import argparse
import re
import time
import threading
import shutil

CMD_SEARCH = 'search'
CMD_LIST = 'list'
CMD_SIZE = 'size'
CMD_RENAME = 'rename'
CMD_DELETE = 'delete'
CMD_COPY = 'copy'
CMD_MOVE = 'move'
COMMANDS = [CMD_SEARCH, CMD_LIST, CMD_SIZE, CMD_RENAME, CMD_DELETE, CMD_COPY, CMD_MOVE]

MATCH_COLOR = '\033[33m' # Yellow
FILE_COLOR = '\033[36m' # Cyan
ERROR_COLOR = '\033[31m' # Red
SUCCESS_COLOR = '\033[32m' # Green
INFO_COLOR = '\033[90m' # Gray
RESET_COLOR = '\033[0m' # Reset

class Spinner:
    def __init__(self, message='', chars="|/-\\"):
        self.message = message
        self.chars = chars
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.clear()

    def clear(self):
        print('\r' + ' ' * (len(self.message) + 5) + '\r', end='', flush=True)  # Clear line

    def _spin(self):
        idx = 0
        while self.running:
            print(f' {self.chars[idx % len(self.chars)]} {self.message}', end='\r', flush=True)
            idx += 1
            time.sleep(0.1)

def fix_path(path: str) -> str:
    """Fixes the path to be uniform across different operating systems."""
    return path.replace('\\', '/').replace('//', '/')

def split_match(match) -> tuple[str, str, str]:
    """Splits a match object into before, match, and after parts."""
    start, end = match.span()
    before = match.string[:start]
    match_text = match.string[start:end]
    after = match.string[end:]
    return before, match_text, after

def regex_sub(match_obj, text: str) -> str:
    """Replaces '$(0)' with the entire match, '$(1)' with group 1, etc."""
    def group_replacer(match):
        idx = int(match.group(1))
        try:
            return match_obj.group(idx)
        except IndexError:
            return ''
    return re.sub(r'\$\((\d+)\)', group_replacer, text)

def get_terminal_width() -> int:
    """Returns the width of the terminal."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # Fallback width if terminal size cannot be determined
    
def get_time_string(elapsed_time: float) -> str:
    hours, rem = divmod(int(elapsed_time), 3600)
    minutes, seconds = divmod(rem, 60)
    milliseconds = int((elapsed_time - int(elapsed_time)) * 10000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:04}"

def get_byte_string(num_bytes: int) -> str:
    """Converts a number of bytes to a human-readable string with 2 decimal places."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024 or unit == 'TB':
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024

def print_summary(title: str, results: dict):
    """Prints a summary of values with a title."""
    # Prepare key-value lines and find max width
    if results:
        max_key_len = max(len(str(k)) for k in results.keys())
        max_val_len = max(len(str(v)) for v in results.values())
    else:
        max_key_len = 0
        max_val_len = 0
    dots_min = 3
    side_space = 2  # 1 space on each side

    # Compute width needed for key-value lines
    avail = max_key_len + dots_min + max_val_len
    box_width = avail + side_space * 2

    # Prepare title
    title = str(title)
    title_width = len(title) + 2  # 1 space on each side
    box_width = max(box_width, title_width + 2)  # +2 for box borders

    # Cap at terminal width
    term_width = get_terminal_width()
    box_width = min(box_width, term_width)
    content_width = box_width - 2

    # Truncate title if needed
    if len(title) + 2 > content_width:
        title = title[:content_width - 3] + "..."

    title_pad = (content_width - len(title)) // 2
    title_line = "|" + " " * title_pad + title + " " * (content_width - len(title) - title_pad) + "|"

    # Prepare key-value lines
    kv_lines = []
    for k, v in results.items():
        key = str(k)
        val = str(v)
        # Truncate key and value if needed
        max_key = max_key_len
        max_val = max_val_len
        avail_val = content_width - (max_key + dots_min)
        if len(key) > max_key:
            key = key[:max_key - 1] + "..." if max_key > 1 else key[:1]
        if avail_val < 1:
            val = val[:1]
        elif len(val) > avail_val:
            val = val[:avail_val - 1] + "..." if avail_val > 1 else val[:1]
        dots = "." * dots_min
        key_pad = key.ljust(max_key, '.')
        line = f"| {key_pad}{dots}{val}{' ' * (content_width - len(key_pad) - dots_min - len(val) - 1)}|"
        kv_lines.append(line)

    # Print box
    print("+" + "-" * content_width + "+")
    print(title_line)
    print("+" + "-" * content_width + "+")
    for line in kv_lines:
        print(line)
    print("+" + "-" * content_width + "+")

def main():
    parser = argparse.ArgumentParser('FileBuddy', f'fb [{"|".join(COMMANDS)}] [options] [-p pattern] [-d directory] [-r recursive] [-o output] [-a hidden] [-v verbose] [-h help]')
    parser.add_argument('command', choices=COMMANDS, help='Command to execute')
    parser.add_argument('options', nargs='*', help='Options for the command')
    parser.add_argument('-p', '--pattern', type=str, help='File pattern to search for')
    parser.add_argument('-d', '--directory', type=str, default='.', help='Directory to operate in (default: current directory)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Search recursively in subdirectories')
    parser.add_argument('-o', '--output', type=str, help='Output file to write results to')
    parser.add_argument('-a', '--all', action='store_true', help='Include hidden files in the search')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    if(len(sys.argv) <= 1):
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    command = getattr(args, 'command', None)
    if command is None:
        print("No command specified. Use -h for help.")
        sys.exit(1)

    if command not in COMMANDS:
        print(f"Unknown command: {command}. Use -h for help.")
        sys.exit(1)
    
    options = getattr(args, 'options', [])
    optionsCount = len(options)
    
    # get pattern, if none, default to all files
    pattern = getattr(args, 'pattern', None)
    if pattern is not None:
        # if pattern is a regex, compile it
        try:
            re.compile(pattern)
        except re.error as e:
            print(f"Invalid regex pattern '{pattern}': {e}")
            sys.exit(1)
    
    # get directory and set it to current directory if not specified
    directory = getattr(args, 'directory', None)
    if directory is not None:
        if not os.path.isdir(directory):
            print(f"Directory '{directory}' does not exist.")
            sys.exit(1)
        else:
            os.chdir(directory)

    # get flags
    recursive = getattr(args, 'recursive', False)
    hidden = getattr(args, 'all', False)
    verbose = getattr(args, 'verbose', False)

    # get output file, if any
    output_file = getattr(args, 'output', None)
    if output_file is not None:
        try:
            output_file = open(output_file, 'w')
        except Exception as e:
            print(f"Could not open output file '{output_file}': {e}")
            sys.exit(1)
    else:
        output_file = None

    tables: list[tuple[str, dict]] = list()

    # get spinner message
    spinnerMessage = ''
    if command == CMD_SEARCH:
        spinnerMessage = 'Searching...'
    elif command == CMD_LIST:
        spinnerMessage = 'Listing...'
    elif command == CMD_SIZE:
        spinnerMessage = 'Sizing...'
    elif command == CMD_RENAME:
        spinnerMessage = 'Renaming...'
    elif command == CMD_DELETE:
        spinnerMessage = 'Deleting...'
    elif command == CMD_COPY:
        spinnerMessage = 'Copying...'
    elif command == CMD_MOVE:
        spinnerMessage = 'Moving...'

    start_time = time.time()

    spinner = Spinner(spinnerMessage)
    spinner.start()

    def print_safe(message: str):
        spinner.clear()
        print(message)

    def print_output(formatted_string: str, match = '', color=MATCH_COLOR, wrapColor = RESET_COLOR):
        if output_file is not None:
            # do not add color to output file
            message = formatted_string.format(match)
            output_file.write(message + '\n')
        else:
            # format the message with color
            message = formatted_string.format(f'{color}{match}{wrapColor}')

            # truncate the message if it is too long for the terminal
            term_width = get_terminal_width()
            if len(message) > term_width:
                # if match is visible, account for the color codes
                if formatted_string.index('{}') < term_width - 3:
                    # truncate the message to fit in the terminal
                    message = message[:term_width - 3 - len(color) - len(wrapColor)] + '...'
                else:
                    # account for color codes
                    message = message[:term_width - 3] + '...'
            print_safe(f'{wrapColor}{message}{RESET_COLOR}')

    def print_error(message):
        # if not verbose output, ignore errors
        if not verbose:
            return
        
        # print error message
        message = f'ERROR: {message}'
        if output_file is not None:
            # do not add color to output file
            output_file.write(f'{message}\n')
        else:
            # format the message with color
            print_safe(f'{ERROR_COLOR}{message}{RESET_COLOR}')
    
    def print_info(message):
        # if not verbose output, ignore info messages
        if not verbose:
            return
        
        # print info message
        message = f'{message}'
        if output_file is not None:
            # do not add color to output file
            output_file.write(f'{message}\n')
        else:
            # format the message with color
            print_safe(f'{INFO_COLOR}{message}{RESET_COLOR}')

    # run different commands
    if command == CMD_SEARCH:
        # contents pattern given in the options
        if optionsCount < 1:
            print(f'No search parameters given. Give a regex pattern to search file contents.')
            sys.exit(1)
        if optionsCount > 1:
            print(f'Too many search parameters given. Give a regex pattern to search file contents.')
            sys.exit(1)

        # get search parameters, if any
        namePattern = pattern
        # try to compile the contents pattern
        contentPattern = options[0]
        try:
            re.compile(contentPattern)
        except re.error as e:
            print(f"Invalid regex pattern '{contentPattern}': {e}")
            sys.exit(1)

        # search all files and directories by walking through them
        results_names = list()
        results_contents = dict()
        results_count = 0
        for root, dirs, files in os.walk(directory):
            # fix path to be uniform
            root = fix_path(root)

            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            results_count += 1

            # print the root directory being searched
            print_info(f'Searching "{root}"')

            # search directory names if namePattern is specified
            if namePattern:
                for dir in dirs:
                    # ignore hidden directories if hidden flag is not set
                    if not hidden and dir.startswith('.'):
                        continue

                    # search the name
                    match_obj = re.search(namePattern, dir)
                    if match_obj:
                        # add to results
                        results_names.append(f'{root}/{dir}/')
                        # print the directory name with match highlighted
                        before, match_text, after = split_match(match_obj)
                        print_output(f'{root}/{before}{{}}{after}/', match_text)

            # search file names and contents if patterns are specified
            for file in files:
                # ignore hidden files if hidden flag is not set
                if not hidden and file.startswith('.'):
                    continue

                full_path = f'{root}/{file}'

                # if name pattern, and file does not match, skip it
                printedFileName = False
                if namePattern:
                    match_obj = re.search(namePattern, file)
                    if not match_obj:
                        continue
                    # add to results
                    results_names.append(full_path)
                    # print the file name with match highlighted
                    before, match_text, after = split_match(match_obj)
                    print_output(f'{root}/{before}{{}}{after}', match_text)
                    printedFileName = True

                # if contents pattern, and file does not match, skip it
                hits = 0
                if contentPattern:
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            contents = f.read().splitlines()
                            for i, line in enumerate(contents):
                                match_obj = re.search(contentPattern, line)
                                if match_obj:                              
                                    if not printedFileName:
                                        # print the file name
                                        print_output(f'{full_path}{{}}')
                                        printedFileName = True
                                    hits += 1
                                    # print the line with match highlighted
                                    before, match_text, after = split_match(match_obj)
                                    print_output(f'    {i + 1}: {before}{{}}{after}', match_text, wrapColor=INFO_COLOR)
                    except Exception as e:
                        print_error(f'Could not read file {full_path}: {e}')
                        continue
                
                if printedFileName:
                    # add to results
                    results_contents[full_path] = hits
            if not recursive:
                break
        tables.append(('Summary', {'Directories Searched': results_count, 'Directories Found': len(results_contents), 'Files Found': len(results_names), 'Hits Found': sum(results_contents.values())}))
        tables.append(('Hits', results_contents))
    elif command == CMD_LIST:
        # contents pattern given in the options
        if optionsCount > 0:
            print(f'Too many search parameters given. Expecting no options.')
            sys.exit(1)

        # search all files and directories by walking through them
        results_file_count = 0
        results_directory_count = 0
        for root, dirs, files in os.walk(directory):
            # fix path to be uniform
            root = fix_path(root)

            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            # search directory names if namePattern is specified
            if pattern:
                for dir in dirs:
                    # ignore hidden directories if hidden flag is not set
                    if not hidden and dir.startswith('.'):
                        continue

                    # search the name
                    if re.search(pattern, dir):
                        print_output(f'{root}/{dir}/')
            else:
                # list all directories
                for dir in dirs:
                    # ignore hidden directories if hidden flag is not set
                    if not hidden and dir.startswith('.'):
                        continue

                    # print the directory name
                    print_output(f'{root}/{dir}/')
                    results_directory_count += 1

            # search file names and contents if patterns are specified
            for file in files:
                # ignore hidden files if hidden flag is not set
                if not hidden and file.startswith('.'):
                    continue

                full_path = f'{root}/{file}'

                # if name pattern, and file does not match, skip it
                if pattern:
                    match_obj = re.search(pattern, file)
                    if not match_obj:
                        continue
                    
                    print_output(f'{root}/{file}')
                    results_file_count += 1
                else: 
                    # list all files

                    # print the file name
                    print_output(f'{root}/{file}')
                    results_file_count += 1
            if not recursive:
                break
        tables.append(('Summary', {'Directory Count': results_directory_count, 'File Count': results_file_count}))
    elif command == CMD_SIZE:
        # contents pattern given in the options
        if optionsCount > 0:
            print(f'Too many search parameters given. Expecting no options.')
            sys.exit(1)

        # search all files and directories by walking through them
        results_sizes: dict[str, int] = dict()
        for root, dirs, files in os.walk(directory, topdown=False):
            # calculate size of each file, add it to results for this root directory
            root = fix_path(root)
            
            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            rootSize = 0

            for dir in dirs:
                # ignore hidden directories if hidden flag is not set
                if not hidden and dir.startswith('.'):
                    continue

                # get the directory size and add it to the results
                full_path = f'{root}/{dir}'
                rootSize += results_sizes.get(full_path, 0)

            for file in files:
                # ignore hidden files if hidden flag is not set
                if not hidden and file.startswith('.'):
                    continue

                # get the file size and add it to the results
                full_path = f'{root}/{file}'
                try:
                    size = os.path.getsize(full_path)
                    rootSize += size
                    results_sizes[full_path] = size
                    print_info(f'"{full_path}" => {get_byte_string(rootSize)}')
                except Exception as e:
                    print_error(f'Could not get size of file {full_path}: {e}')
                    continue

            # add the root directory size to the results
            results_sizes[root] = rootSize
            print_info(f'"{root}" => {get_byte_string(rootSize)}')
            
        # go through the results and print them
        for root, dirs, files in os.walk(directory):
            # fix path to be uniform
            root = fix_path(root)

            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            # search directory names if namePattern is specified
            for dir in dirs:
                # ignore hidden directories if hidden flag is not set
                if not hidden and dir.startswith('.'):
                    continue

                # if name pattern, and directory does not match, skip it
                if pattern and not re.search(pattern, dir):
                    continue

                # print the directory name with size
                full_path = f'{root}/{dir}'
                size = results_sizes.get(full_path, 0)
                print_output(f'{full_path}/ => {get_byte_string(size)}')
            
            for file in files:
                # ignore hidden files if hidden flag is not set
                if not hidden and file.startswith('.'):
                    continue

                full_path = f'{root}/{file}'

                # if name pattern, and file does not match, skip it
                if pattern and not re.search(pattern, file):
                    continue

                # print the file name with size
                size = results_sizes.get(full_path, 0)
                print_output(f'{full_path} => {get_byte_string(size)}')
            
            if not recursive:
                break
        tables.append(('Summary', {}))
    elif command == CMD_RENAME:
        # check options
        if optionsCount < 1:
            print(f'Not enough options given. Expecting 1 option: <new_name>')
            sys.exit(1)
        if optionsCount > 1:
            print(f'Too many options given. Expecting 1 option: <new_name>')
            sys.exit(1)

        new_name = options[0]

        if not pattern:
            print(f'No pattern specified. Expecting a pattern to rename files.')
            sys.exit(1)

        # search all files and directories by walking through them
        results_directories = 0
        results_files = 0
        for root, dirs, files in os.walk(directory):
            root = fix_path(root)
            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            def rename(old_name: str, new_name: str) -> bool:
                # ignore hidden directories if hidden flag is not set
                if not hidden and old_name.startswith('.'):
                    return False

                # if name pattern, and directory does not match, skip it
                match_obj = re.search(pattern, old_name)
                if not match_obj:
                    return False

                old_path = f'{root}/{old_name}'
                new_path = f'{root}/{regex_sub(match_obj, new_name)}'

                try:
                    os.rename(old_path, new_path)
                    print_output(f'{old_path} => {new_path}')
                    return True
                except Exception as e:
                    print_error(f'Could not rename directory {old_path}: {e}')
                    return False
                
            for dir in dirs:
                if rename(dir, new_name):
                    results_directories += 1
            for file in files:
                if rename(file, new_name):
                    results_files += 1

            if not recursive:
                break
        tables.append(('Summary', {"Directories renamed: ": results_directories, "Files renamed: ": results_files}))
    elif command == CMD_DELETE:
        # check options
        if optionsCount > 0:
            print(f'Too many options given. Expecting no options.')
            sys.exit(1)

        if not pattern:
            print(f'No pattern specified. Expecting a pattern to delete files.')
            sys.exit(1)

        # search all files and directories by walking through them
        results_directories = 0
        results_files = 0
        for root, dirs, files in os.walk(directory):
            root = fix_path(root)
            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            def delete(name: str, directory: bool) -> bool:
                # ignore hidden directories if hidden flag is not set
                if not hidden and name.startswith('.'):
                    return False

                # if name pattern, and directory does not match, skip it
                match_obj = re.search(pattern, name)
                if not match_obj:
                    return False
                
                full_path = f'{root}/{name}'

                try:
                    if directory:
                        # remove sub directories
                        for sub_root, sub_dirs, sub_files in os.walk(full_path, topdown=False):
                            for sub_file in sub_files:
                                sub_path = os.path.join(sub_root, sub_file)
                                os.remove(sub_path)
                                print_info(f'Deleted file: {sub_path}')
                            for sub_dir in sub_dirs:
                                sub_path = os.path.join(sub_root, sub_dir)
                                os.rmdir(sub_path)
                                print_info(f'Deleted directory: {sub_path}')
                        # remove the directory itself
                        os.rmdir(full_path)
                    else:
                        # remove the file
                        os.remove(full_path)
                    print_output(f'{full_path}')
                    return True
                except Exception as e:
                    print_error(f'Could not rename directory {name}: {e}')
                    return False
                
            for dir in dirs:
                if delete(dir, True):
                    results_directories += 1
            for file in files:
                if delete(file, False):
                    results_files += 1

            if not recursive:
                break
        tables.append(('Summary', {"Directories deleted: ": results_directories, "Files deleted: ": results_files}))
    elif command == CMD_COPY:
        # check options
        if optionsCount < 1:
            print(f'Not enough options given. Expecting 1 option: <output_dir|output_file>')
            sys.exit(1)
        if optionsCount > 1:
            print(f'Too many options given. Expecting 1 option: <output_dir|output_file>')
            sys.exit(1)

        output_path = options[0]

        if not pattern:
            print(f'No pattern specified. Expecting a pattern to copy files.')
            sys.exit(1)

        results_directories = 0
        results_files = 0
        for root, dirs, files in os.walk(directory):
            root = fix_path(root)
            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            def move_item(name: str, destination: str, is_dir: bool) -> bool:
                # ignore hidden directories if hidden flag is not set
                if not hidden and name.startswith('.'):
                    return False
                
                # if name does not match the pattern, skip it
                match_obj = re.search(pattern, name)
                if not match_obj:
                    return False

                from_path = f'{root}/{name}'
                if not is_dir and destination.endswith('/'):
                    destination += name
                elif is_dir and os.path.isdir(destination):
                    if destination.endswith('/'):
                        destination += name
                    else:
                        destination += f'/{name}'
                to_path = f'{regex_sub(match_obj, destination)}'

                # copy the contents
                if is_dir:
                    try:
                        shutil.copytree(from_path, to_path, dirs_exist_ok=True)
                    except shutil.Error as e:
                        print_error(f'Could not copy directory {from_path} to {to_path}: {e}')
                        return False
                else:
                    try:
                        shutil.copy2(from_path, to_path)
                    except shutil.Error as e:
                        print_error(f'Could not copy file {from_path} to {to_path}: {e}')
                        return False
                print_output(f'{from_path} => {to_path}')
                return True

            for dir in dirs:
                if move_item(dir, output_path, True):
                    results_directories += 1
            for file in files:
                if move_item(file, output_path, False):
                    results_files += 1

            if not recursive:
                break
        tables.append(('Summary', {"Directories copied: ": results_directories, "Files copied: ": results_files}))
    elif command == CMD_MOVE:
        # check options
        if optionsCount < 1:
            print(f'Not enough options given. Expecting 1 option: <output_dir|output_file>')
            sys.exit(1)
        if optionsCount > 1:
            print(f'Too many options given. Expecting 1 option: <output_dir|output_file>')
            sys.exit(1)

        output_path = options[0]

        if not pattern:
            print(f'No pattern specified. Expecting a pattern to move files.')
            sys.exit(1)

        results_directories = 0
        results_files = 0
        for root, dirs, files in os.walk(directory):
            root = fix_path(root)
            # ignore hidden files and directories if hidden flag is not set
            if not hidden and '/.' in root:
                continue

            def move_item(name: str, destination: str, is_dir: bool) -> bool:
                # ignore hidden directories if hidden flag is not set
                if not hidden and name.startswith('.'):
                    return False
                
                # if name does not match the pattern, skip it
                match_obj = re.search(pattern, name)
                if not match_obj:
                    return False

                from_path = f'{root}/{name}'
                if not is_dir and destination.endswith('/'):
                    destination += name
                elif is_dir and os.path.isdir(destination):
                    if destination.endswith('/'):
                        destination += name
                    else:
                        destination += f'/{name}'
                to_path = f'{regex_sub(match_obj, destination)}'

                # copy the contents
                try:
                    shutil.move(from_path, to_path)
                except shutil.Error as e:
                    print_error(f'Could not move directory {from_path} to {to_path}: {e}')
                    return False
                print_output(f'{from_path} => {to_path}')
                return True

            for dir in dirs:
                if move_item(dir, output_path, True):
                    results_directories += 1
            for file in files:
                if move_item(file, output_path, False):
                    results_files += 1

            if not recursive:
                break
        tables.append(('Summary', {"Directories moved: ": results_directories, "Files moved: ": results_files}))

    spinner.stop()

    # stop timer
    end_time = time.time()

    # add elapsed time to first table (presumable the summary)
    elapsed_time = end_time - start_time
    elapsed_str = get_time_string(elapsed_time)
    tables[0][1]['Elapsed Time'] = elapsed_str

    # print all tables
    for title, results in tables:
        print_summary(title, results)

    # close output file
    if output_file is not None:
        output_file.close()


if __name__ == "__main__":
    main()