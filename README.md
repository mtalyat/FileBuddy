# FileBuddy

![FileBuddy Icon](Images/Icon_Scaled.png)

FileBuddy is a utility Python script, intended to make quickly modifying, searching, and working with files easy.

## Usage

1. Make sure you have Python 3 installed.
2. Download the repository.
3. Add the Source directory within the repository to your system environment variables.
4. Open a terminal and run FileBuddy.

General form of command:

    fb <command> <options> [-p pattern] [-d directory] [-r recursive] [-o output] [-f format] [-a hidden] [-v verbose] [-h help]

OR

    python fb.py <command> <options> [-p pattern] [-d directory] [-r recursive] [-o output] [-f format] [-a hidden] [-v verbose] [-h help]

## Commands

Going in place of `<command>`.

| Command | Example | Description |
| --- | --- | --- |
| search | `fb search "\bPattern\b" -p "\.txt$"` | Searches file contents using the given regex pattern (supports whole-file and multiline matches). |
| find | `fb find "\bPattern\b" -p "\.txt$"` | Alias for `search`. |
| extract | `fb extract "Hello (.*)" -p "\.txt$"` | Searches file contents and prints captured regex groups for each match. |
| `replace` | `fb replace "myTpyo" "myTypo"` | Searches file contents with the given regex pattern and replaces each match with the replacement text (supports multiline). |
| list | `fb list -r` | Lists the files and directories. |
| size | `fb size -a` | Lists the sizes of each file and directory. |
| rename | `fb rename "$1pp" -p "^(.*)\.h$"` | Renames the files and directories. |
| delete | `fb delete -p ".*\.txt"` | Deletes the files and directories.
| copy | `fb copy "C:/destination" -p ".*\.txt"` | Copies the files and directories to the given destination path. |
| move | `fb move "C:/destination" -p ".*\.txt"` | Moves the files and directories to the given destination path. |

**Notes**

Only search/find, extract, replace, rename, copy and move use `<options>`.

For rename, copy, move, and replace, use `$0`, `$1`, `$2`, etc. in destination or replacement text, where `$0` is the full regex match and `$1+` are capture groups.

For replace, escaped characters in replacement text are decoded before applying group substitution. For example: `\n`, `\t`, `\r`, `\b`, `\f`, `\v`, and `\\`.

For search, extract, and replace, the `-p` pattern filters file names before reading file contents.

For rename, copy, move, and delete, you can use the `-y` argument to skip the confirmation.

It is recommended to use `-a` with `size` to ensure you get the proper sizes of directories. Otherwise, hidden sub-directories and files are ignored, which may yield invalid results.

## Flags

| Flag | Example | Description |
| --- | --- | --- |
| `-h`, `--help` | `-h` | Displays the help message. |
| `-p`, `--pattern` | `-p "\d+"` | Defines what regex pattern to use to filter the files and directories. Defaults to use all files and directories within the working directory. |
| `-d`, `--directory` | `-d "../Source"` | Defines the working directory. Defaults to `.`. |
| `-r`, `--recursive` | `-r` | If given, the operations on directories will be recursive. |
| `-o`, `--output` | `-o "log.txt"` | If given, all output will be redirected to a file. If not given, the output is printed in the terminal. The active output file is automatically excluded from command processing. |
| `-f`, `--format` | `-f "($0)"` | If given, formats each emitted output element. Use `$0` for the full emitted string and `$1`, `$2`, etc. for regex capture groups when the element comes from a regex match. |
| `-a`, `--all` | `-a` | Includes hidden directories and files in the search. |
| `-v`, `--verbose` | `-v` | Outputs additional information for some commands. |
| `-y`, `--yes` | `-y` | Automatically confirms all confirmation prompts. |
| `-s`, `--summary` | `-s` | Prints a summary result table after the operation has completed. |
| `--nocolor` | `--nocolor` | Removes the ANSI color codes from the printed output. Log file outputs (when using -o) never have ANSI codes. |

When `-f` is omitted, commands keep their current output format.

PowerShell note: `"$0"` may be expanded by the shell before reaching FileBuddy. `--format` now defaults to `$0` when no value is provided, and you can also pass a literal using single quotes, for example `--format '$0'`.
